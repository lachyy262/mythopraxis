"""Validate adaptive workflow graphs and persist private human-readable traces."""

import json
import hashlib
import os
import stat
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from mythopraxis.approaches import compose_approach, validate_approach
from mythopraxis.cases import validate_case
from mythopraxis.contracts import load_contract, validate_instance
from mythopraxis.inputs import MAX_INPUT_BYTES, MAX_PROMPT_CHARS, create_private_parents

WORKFLOW_SCHEMA = "workflow.schema.json"
STATE_SCHEMA = "workflow-state.schema.json"
MAX_TRACE_EVENTS = 200
MAX_NOTE_CHARS = 2000


class WorkflowError(ValueError):
    """Raised when a workflow, proposal, or persisted run is invalid."""


def validate_workflow(workflow: Any, approach: dict[str, Any]) -> list[str]:
    """Validate workflow fields and graph reachability against an approach."""
    approach_errors = validate_approach(approach)
    if approach_errors:
        return [f"invalid approach: {error}" for error in approach_errors]
    errors = validate_instance(workflow, load_contract(WORKFLOW_SCHEMA))
    if errors or not isinstance(workflow, dict):
        return errors
    phase_ids = {phase["id"] for phase in approach["phases"]}
    if workflow["approach_id"] != approach["id"]:
        errors.append("workflow approach_id does not match the supplied approach")
    if workflow["start_phase"] not in phase_ids:
        errors.append(f"unknown start phase {workflow['start_phase']}")
    routes = workflow["routes"]
    route_ids = [route["id"] for route in routes]
    for identifier in sorted(set(route_ids)):
        if route_ids.count(identifier) > 1:
            errors.append(f"duplicate route id {identifier}")
    adjacency: dict[str, set[str]] = {phase_id: set() for phase_id in phase_ids}
    reverse: dict[str, set[str]] = {phase_id: set() for phase_id in phase_ids}
    outgoing: set[str] = set()
    for route in routes:
        source, target = route["from_phase"], route["to_phase"]
        if source not in phase_ids:
            errors.append(f"route {route['id']} has unknown source phase {source}")
            continue
        outgoing.add(source)
        if target != "complete":
            if target not in phase_ids:
                errors.append(f"route {route['id']} has unknown target phase {target}")
                continue
            adjacency[source].add(target)
            reverse[target].add(source)
    for phase_id in sorted(phase_ids - outgoing):
        errors.append(f"phase {phase_id} has no outgoing route")
    if workflow["start_phase"] in phase_ids:
        reachable = _closure(workflow["start_phase"], adjacency)
        for phase_id in sorted(phase_ids - reachable):
            errors.append(f"phase {phase_id} is unreachable from the start phase")
        finishable = {route["from_phase"] for route in routes if route["to_phase"] == "complete"}
        can_finish = set(finishable)
        frontier = list(finishable)
        while frontier:
            node = frontier.pop()
            for prior in reverse.get(node, set()) - can_finish:
                can_finish.add(prior)
                frontier.append(prior)
        for phase_id in sorted(reachable - can_finish):
            errors.append(f"phase {phase_id} cannot reach complete")
        completion_distance = {route["from_phase"]: 1 for route in routes if route["to_phase"] == "complete"}
        frontier = list(completion_distance)
        while frontier:
            node = frontier.pop(0)
            for prior in reverse.get(node, set()):
                if prior not in completion_distance:
                    completion_distance[prior] = completion_distance[node] + 1
                    frontier.append(prior)
        minimum_steps = completion_distance.get(workflow["start_phase"])
        if minimum_steps is not None and workflow["max_steps"] < minimum_steps:
            errors.append(f"max_steps must allow at least {minimum_steps} transitions to complete")
    return sorted(set(errors))


def _closure(start: str, graph: dict[str, set[str]]) -> set[str]:
    visited = set()
    frontier = [start]
    while frontier:
        node = frontier.pop()
        if node in visited:
            continue
        visited.add(node)
        frontier.extend(graph.get(node, set()) - visited)
    return visited


def load_workflow(path: Path, approach: dict[str, Any]) -> dict[str, Any]:
    """Load a JSON/YAML workflow and enforce its trusted packaged schema."""
    from mythopraxis.inputs import load_yaml

    data = load_yaml(path)
    errors = validate_workflow(data, approach)
    if errors:
        raise WorkflowError("; ".join(errors))
    return data


def _validate_inputs(case: Any, approach: Any, workflow: Any) -> list[str]:
    errors = validate_case(case)
    errors.extend(f"invalid approach: {error}" for error in validate_approach(approach))
    if not errors:
        errors.extend(validate_workflow(workflow, approach))
    return errors


def initialize_run(
    path: Path, case: dict[str, Any], approach: dict[str, Any], workflow: dict[str, Any]
) -> dict[str, Any]:
    """Create a private run file exclusively, retaining IDs but no case contents."""
    errors = _validate_inputs(case, approach, workflow)
    if errors:
        raise WorkflowError("; ".join(errors))
    path = path.expanduser().absolute()
    create_private_parents(path.parent)
    state = {
        "state_version": "1.0",
        "run_id": uuid4().hex,
        "case_id": case["id"],
        "approach_id": approach["id"],
        "approach_digest": _document_digest(approach),
        "workflow_id": workflow["id"],
        "workflow_digest": _workflow_digest(workflow),
        "current_phase": workflow["start_phase"],
        "status": "active",
        "step": 0,
        "step_limit": workflow["max_steps"],
        "pending_route": None,
        "events": [],
    }
    encoded = _encode_state(state)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    return state


def load_run(path: Path, workflow: dict[str, Any], approach: dict[str, Any]) -> dict[str, Any]:
    """Load bounded, private JSON state and reject tampering or stale run files."""
    path = path.expanduser()
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise WorkflowError("run state must be a regular non-symlink file")
        if os.name == "posix" and info.st_mode & 0o077:
            raise WorkflowError("run state permissions must be private (0600)")
        if info.st_size > MAX_INPUT_BYTES:
            raise WorkflowError(f"run state exceeds {MAX_INPUT_BYTES} bytes")
        state = json.loads(path.read_text(encoding="utf-8"))
    except WorkflowError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise WorkflowError(f"cannot read run state: {error}") from error
    if not isinstance(state, dict):
        raise WorkflowError("run state must be an object")
    state_errors = validate_instance(state, load_contract(STATE_SCHEMA))
    if state_errors:
        raise WorkflowError("invalid run state: " + "; ".join(state_errors))
    _assert_context(state, workflow, approach)
    phases = {route["from_phase"] for route in workflow["routes"]}
    targets = {route["to_phase"] for route in workflow["routes"] if route["to_phase"] != "complete"}
    phases |= targets
    valid = (
        state.get("state_version") == "1.0"
        and isinstance(state.get("run_id"), str)
        and isinstance(state.get("case_id"), str)
        and state.get("approach_id") == workflow["approach_id"]
        and state.get("current_phase") in phases | {"complete"}
        and state.get("status") in {"active", "awaiting_author", "awaiting_approval", "complete"}
        and type(state.get("step")) is int
        and 0 <= state["step"] <= 100
        and type(state.get("step_limit")) is int
        and workflow["max_steps"] <= state["step_limit"] <= 100
        and state["step"] <= state["step_limit"]
        and isinstance(state.get("events"), list)
        and len(state["events"]) <= MAX_TRACE_EVENTS
        and (state.get("pending_route") is None or isinstance(state.get("pending_route"), str))
    )
    if not valid:
        raise WorkflowError("run state is malformed or has an invalid step")
    if (state["status"] == "complete") != (state["current_phase"] == "complete"):
        raise WorkflowError("run state status does not match its current phase")
    if state["status"] != "awaiting_approval" and state["pending_route"] is not None:
        raise WorkflowError("run state has a pending route outside an approval pause")
    if state["status"] == "awaiting_approval":
        route = _route(workflow, state["pending_route"])
        if route is None or not route["human_approval"] or route["from_phase"] != state["current_phase"]:
            raise WorkflowError("run state has an invalid pending approval")
    return state


def phase_packet(
    case: dict[str, Any], approach: dict[str, Any], workflow: dict[str, Any], state: dict[str, Any]
) -> str:
    """Render a bounded phase packet with routes and the concise decision trace."""
    _check_state_context(case, approach, workflow, state)
    if state["status"] != "active":
        raise WorkflowError(f"run is {state['status']}; resolve that pause before continuing")
    packet = compose_approach(case, approach, state["current_phase"])
    routes = [route for route in workflow["routes"] if route["from_phase"] == state["current_phase"]]
    orchestration = {
        "workflow": {"id": workflow["id"], "title": workflow["title"], "step": state["step"], "step_limit": state["step_limit"]},
        "available_routes": routes,
        "recent_decisions": state["events"][-10:],
    }
    packet += "\n## Adaptive workflow context\n\n"
    packet += json.dumps(orchestration, ensure_ascii=False, indent=2)
    packet += "\n\nUse the route conditions as authored possibilities, not mandatory instructions. Choose a route only when the evidence supports it. If none fits, pause for the author and state what is missing. Record the specific evidence and reasoning behind each transition. If the step budget is exhausted, ask the author to extend it. Do not call providers or tools through this workflow command.\n"
    if len(packet) > MAX_PROMPT_CHARS:
        raise WorkflowError(f"orchestration packet exceeds the {MAX_PROMPT_CHARS}-character limit")
    return packet


def record_proposal(
    path: Path,
    state: dict[str, Any],
    workflow: dict[str, Any],
    route_id: str | None,
    evidence: str,
    rationale: str,
    *,
    pause: bool = False,
) -> dict[str, Any]:
    """Record a route choice or an explicit no-match pause, then persist it."""
    _assert_active(state, workflow)
    _note(evidence, "evidence")
    _note(rationale, "rationale")
    next_state = json.loads(json.dumps(state))
    if pause:
        if route_id is not None:
            raise WorkflowError("a paused proposal cannot include a route")
        next_state["status"] = "awaiting_author"
        kind = "author_pause"
    else:
        route = _route(workflow, route_id)
        if route is None or route["from_phase"] != state["current_phase"]:
            raise WorkflowError("route must leave the current phase")
        _advance_step(next_state, workflow)
        if route["human_approval"]:
            next_state["status"] = "awaiting_approval"
            next_state["pending_route"] = route_id
        else:
            _transition(next_state, route)
        kind = "route_proposal"
    _append_event(next_state, {"kind": kind, "from_phase": state["current_phase"], "route_id": route_id, "evidence": evidence, "rationale": rationale})
    return _persist(path, next_state, state)


def approve_route(path: Path, state: dict[str, Any], workflow: dict[str, Any], route_id: str) -> dict[str, Any]:
    """Record explicit human approval and follow the pending route."""
    _assert_workflow(state, workflow)
    if state["status"] != "awaiting_approval" or state.get("pending_route") != route_id:
        raise WorkflowError("run is not awaiting approval for that route")
    route = _route(workflow, route_id)
    if route is None or not route["human_approval"] or route["from_phase"] != state["current_phase"]:
        raise WorkflowError("route is not valid for this pending approval")
    next_state = json.loads(json.dumps(state))
    _transition(next_state, route)
    _append_event(next_state, {"kind": "human_approval", "from_phase": state["current_phase"], "route_id": route_id})
    return _persist(path, next_state, state)


def reject_route(path: Path, state: dict[str, Any], workflow: dict[str, Any], route_id: str, rationale: str) -> dict[str, Any]:
    """Record a human rejection and return the run to the same active phase."""
    _assert_workflow(state, workflow)
    if state["status"] != "awaiting_approval" or state.get("pending_route") != route_id:
        raise WorkflowError("run is not awaiting approval for that route")
    _note(rationale, "rejection rationale")
    next_state = json.loads(json.dumps(state))
    next_state["status"] = "active"
    next_state["pending_route"] = None
    _append_event(next_state, {"kind": "human_rejection", "from_phase": state["current_phase"], "route_id": route_id, "rationale": rationale})
    return _persist(path, next_state, state)


def select_route(path: Path, state: dict[str, Any], workflow: dict[str, Any], route_id: str, rationale: str) -> dict[str, Any]:
    """Let the workflow author resolve a no-match pause with an explicit choice."""
    _assert_workflow(state, workflow)
    if state["status"] != "awaiting_author":
        raise WorkflowError("run is not awaiting_author")
    _note(rationale, "selection rationale")
    route = _route(workflow, route_id)
    if route is None or route["from_phase"] != state["current_phase"]:
        raise WorkflowError("selected route must leave the current phase")
    next_state = json.loads(json.dumps(state))
    _advance_step(next_state, workflow)
    _transition(next_state, route)
    _append_event(next_state, {"kind": "author_selection", "from_phase": state["current_phase"], "route_id": route_id, "rationale": rationale})
    return _persist(path, next_state, state)


def extend_run(path: Path, state: dict[str, Any], workflow: dict[str, Any], step_limit: int, rationale: str) -> dict[str, Any]:
    """Let an author explicitly extend a bounded run without editing its workflow."""
    _assert_workflow(state, workflow)
    if state["status"] == "complete":
        raise WorkflowError("a completed run cannot be extended")
    if type(step_limit) is not int or not state["step_limit"] < step_limit <= 100:
        raise WorkflowError("new step limit must be greater than the current limit and at most 100")
    _note(rationale, "extension rationale")
    next_state = json.loads(json.dumps(state))
    next_state["step_limit"] = step_limit
    _append_event(next_state, {"kind": "author_extension", "from_phase": state["current_phase"], "rationale": rationale})
    return _persist(path, next_state, state)


def _check_state_context(case: dict[str, Any], approach: dict[str, Any], workflow: dict[str, Any], state: dict[str, Any]) -> None:
    errors = _validate_inputs(case, approach, workflow)
    if errors:
        raise WorkflowError("; ".join(errors))
    if state["case_id"] != case["id"] or state["approach_id"] != approach["id"] or state["workflow_id"] != workflow["id"]:
        raise WorkflowError("run state does not match the supplied case, approach, and workflow")
    _assert_context(state, workflow, approach)


def _assert_active(state: dict[str, Any], workflow: dict[str, Any]) -> None:
    _assert_workflow(state, workflow)
    if state.get("status") != "active":
        raise WorkflowError(f"run is {state.get('status')}; resolve that pause before continuing")


def _assert_workflow(state: dict[str, Any], workflow: dict[str, Any]) -> None:
    if state.get("workflow_id") != workflow["id"]:
        raise WorkflowError("run state does not match this workflow")
    if state.get("workflow_digest") != _workflow_digest(workflow):
        raise WorkflowError("workflow changed after this run started")


def _assert_context(state: dict[str, Any], workflow: dict[str, Any], approach: dict[str, Any]) -> None:
    _assert_workflow(state, workflow)
    if state.get("approach_id") != approach["id"]:
        raise WorkflowError("run state does not match this approach")
    if state.get("approach_digest") != _document_digest(approach):
        raise WorkflowError("approach changed after this run started")


def _route(workflow: dict[str, Any], route_id: str | None) -> dict[str, Any] | None:
    if route_id is None:
        return None
    return next((route for route in workflow["routes"] if route["id"] == route_id), None)


def _note(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_NOTE_CHARS:
        raise WorkflowError(f"{name} must contain 1 to {MAX_NOTE_CHARS} characters")


def _advance_step(state: dict[str, Any], workflow: dict[str, Any]) -> None:
    if state["step"] >= state["step_limit"]:
        raise WorkflowError("run step limit reached; an author must extend the budget")
    state["step"] += 1


def _transition(state: dict[str, Any], route: dict[str, Any]) -> None:
    state["current_phase"] = route["to_phase"]
    state["pending_route"] = None
    state["status"] = "complete" if route["to_phase"] == "complete" else "active"


def _append_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    if len(state["events"]) >= MAX_TRACE_EVENTS:
        raise WorkflowError("workflow trace event limit reached")
    normalized = {"route_id": None, "evidence": None, "rationale": None, **event}
    state["events"].append({"at": datetime.now(timezone.utc).isoformat(), **normalized})


def _encode_state(state: dict[str, Any]) -> bytes:
    encoded = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(encoded) > MAX_INPUT_BYTES:
        raise WorkflowError(f"run state exceeds {MAX_INPUT_BYTES} bytes")
    return encoded


def _workflow_digest(workflow: dict[str, Any]) -> str:
    return _document_digest(workflow)


def _document_digest(document: dict[str, Any]) -> str:
    canonical = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@contextmanager
def _run_lock(path: Path):
    """Hold an OS lock whose ownership is released automatically on process exit."""
    lock_path = path.with_name(path.name + ".lock")
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as error:
        raise WorkflowError(f"cannot open run lock: {error}") from error
    locked = False
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or (os.name == "posix" and info.st_mode & 0o077):
            raise WorkflowError("run lock must be a private regular file")
        if os.name == "posix":
            import fcntl

            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise WorkflowError("run is locked for update; retry after the other update finishes") from error
            locked = True
        elif os.name == "nt":
            import msvcrt

            if info.st_size == 0:
                os.write(descriptor, b"0")
            os.lseek(descriptor, 0, os.SEEK_SET)
            try:
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise WorkflowError("run is locked for update; retry after the other update finishes") from error
            locked = True
        else:
            raise WorkflowError("run locking is unsupported on this platform")
        yield
    finally:
        try:
            if locked and os.name == "posix":
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_UN)
            elif locked and os.name == "nt":
                import msvcrt

                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
        finally:
            os.close(descriptor)


def _persist(path: Path, state: dict[str, Any], expected_state: dict[str, Any]) -> dict[str, Any]:
    path = path.expanduser().absolute()
    temporary = None
    with _run_lock(path):
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise WorkflowError("run state must be a regular non-symlink file")
            if os.name == "posix" and info.st_mode & 0o077:
                raise WorkflowError("run state permissions must be private (0600)")
            if info.st_size > MAX_INPUT_BYTES:
                raise WorkflowError(f"run state exceeds {MAX_INPUT_BYTES} bytes")
            current_state = json.loads(path.read_text(encoding="utf-8"))
            if current_state != expected_state:
                raise WorkflowError("run state changed since it was read; reload before retrying")
            encoded = _encode_state(state)
            descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except (OSError, json.JSONDecodeError) as error:
            raise WorkflowError(f"cannot update run state: {error}") from error
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
    return state
