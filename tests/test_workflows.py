import json
import os
import shutil
from pathlib import Path

import pytest

from mythopraxis.cli import main
from mythopraxis.workflows import (
    WorkflowError,
    approve_route,
    extend_run,
    initialize_run,
    load_run,
    record_proposal,
    reject_route,
    select_route,
    validate_workflow,
)
from mythopraxis.validation import validate_repository

from test_approaches import sample_approach, sample_case, write_yaml


def sample_workflow() -> dict:
    return {
        "workflow_version": "1.0",
        "id": "evidence-led-response",
        "title": "Evidence-led response",
        "approach_id": "investigate-and-respond",
        "start_phase": "orient",
        "max_steps": 12,
        "no_match": "pause-for-author",
        "routes": [
            {"id": "need-evidence", "from_phase": "orient", "to_phase": "investigate", "when": "A consequential fact remains unverified.", "human_approval": False},
            {"id": "ready-to-respond", "from_phase": "orient", "to_phase": "respond", "when": "The available evidence already supports a safe response.", "human_approval": False},
            {"id": "respond-after-review", "from_phase": "investigate", "to_phase": "respond", "when": "The evidence supports a bounded response.", "human_approval": True},
            {"id": "finish", "from_phase": "respond", "to_phase": "complete", "when": "The person has a clear outcome and owner for follow-through.", "human_approval": False},
        ],
    }


def create_inputs(tmp_path: Path):
    case_path = write_yaml(tmp_path / "case.yaml", sample_case())
    approach_path = write_yaml(tmp_path / "approach.yaml", sample_approach())
    workflow_path = write_yaml(tmp_path / "workflow.yaml", sample_workflow())
    return case_path, approach_path, workflow_path


def test_workflow_validates_graph_against_approach():
    assert validate_workflow(sample_workflow(), sample_approach()) == []


def test_workflow_rejects_unreachable_phase_and_unfinishable_branch():
    workflow = sample_workflow()
    workflow["routes"] = workflow["routes"][:-1]

    errors = validate_workflow(workflow, sample_approach())

    assert any("respond" in error and "outgoing" in error for error in errors)


def test_run_state_is_private_and_refuses_overwrite(tmp_path: Path):
    state_path = tmp_path / "private" / "run.json"

    state = initialize_run(state_path, sample_case(), sample_approach(), sample_workflow())

    assert state["status"] == "active"
    assert state["current_phase"] == "orient"
    if os.name == "posix":
        assert state_path.stat().st_mode & 0o777 == 0o600
        assert state_path.parent.stat().st_mode & 0o777 == 0o700
    with pytest.raises(FileExistsError):
        initialize_run(state_path, sample_case(), sample_approach(), sample_workflow())


def test_route_proposal_and_approval_record_adaptive_handoff(tmp_path: Path):
    state_path = tmp_path / "run.json"
    state = initialize_run(state_path, sample_case(), sample_approach(), sample_workflow())

    state = record_proposal(state_path, state, sample_workflow(), "need-evidence", "Settlement status is not known.", "The unknown changes the recommendation.")
    assert state["current_phase"] == "investigate"
    assert state["status"] == "active"
    assert state["events"][-1]["route_id"] == "need-evidence"

    state = record_proposal(state_path, state, sample_workflow(), "respond-after-review", "Internal status confirms processing.", "A bounded response is supported.")
    assert state["status"] == "awaiting_approval"
    assert state["current_phase"] == "investigate"

    state = approve_route(state_path, state, sample_workflow(), "respond-after-review")
    assert state["current_phase"] == "respond"
    assert state["status"] == "active"
    assert state["events"][-1]["kind"] == "human_approval"


def test_no_match_pauses_until_author_selects_a_route(tmp_path: Path):
    state_path = tmp_path / "run.json"
    state = initialize_run(state_path, sample_case(), sample_approach(), sample_workflow())

    state = record_proposal(state_path, state, sample_workflow(), None, "The available facts conflict.", "Neither route condition is supported.", pause=True)
    assert state["status"] == "awaiting_author"
    with pytest.raises(WorkflowError, match="awaiting_author"):
        record_proposal(state_path, state, sample_workflow(), "need-evidence", "x", "y")

    state = select_route(state_path, state, sample_workflow(), "need-evidence", "Collect the authoritative status before choosing.")
    assert state["current_phase"] == "investigate"
    assert state["events"][-1]["kind"] == "author_selection"


def test_human_can_reject_a_gated_route_for_reconsideration(tmp_path: Path):
    workflow = sample_workflow()
    state_path = tmp_path / "run.json"
    state = initialize_run(state_path, sample_case(), sample_approach(), workflow)
    state = record_proposal(state_path, state, workflow, "need-evidence", "The status is unknown.", "It could change the recommendation.")
    state = record_proposal(state_path, state, workflow, "respond-after-review", "Status is still incomplete.", "A response needs human review.")

    state = reject_route(state_path, state, workflow, "respond-after-review", "The evidence is not sufficient for this transition.")

    assert state["status"] == "active"
    assert state["current_phase"] == "investigate"
    assert state["events"][-1]["kind"] == "human_rejection"


def test_stale_or_foreign_run_is_rejected(tmp_path: Path):
    state_path = tmp_path / "run.json"
    state = initialize_run(state_path, sample_case(), sample_approach(), sample_workflow())
    foreign = sample_workflow()
    foreign["id"] = "other-workflow"

    with pytest.raises(WorkflowError, match="does not match"):
        record_proposal(state_path, state, foreign, "need-evidence", "Evidence", "Reason")

    changed = sample_workflow()
    changed["routes"][0]["when"] = "A different evidence condition now applies."
    with pytest.raises(WorkflowError, match="changed after this run started"):
        load_run(state_path, changed, sample_approach())

    changed_approach = sample_approach()
    changed_approach["phases"][0]["intent"] = "A different phase intent, retaining the same approach ID."
    with pytest.raises(WorkflowError, match="approach changed after this run started"):
        load_run(state_path, sample_workflow(), changed_approach)

    state["step"] = 999
    state_path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(WorkflowError, match="invalid run state"):
        load_run(state_path, sample_workflow(), sample_approach())


def test_run_state_rejects_permissive_mode_and_symlinks(tmp_path: Path):
    state_path = tmp_path / "run.json"
    initialize_run(state_path, sample_case(), sample_approach(), sample_workflow())
    state_path.chmod(0o644)
    with pytest.raises(WorkflowError, match="permissions"):
        load_run(state_path, sample_workflow(), sample_approach())

    state_path.chmod(0o600)
    alias = tmp_path / "alias.json"
    alias.symlink_to(state_path)
    with pytest.raises(WorkflowError, match="non-symlink"):
        load_run(alias, sample_workflow(), sample_approach())


def test_workflow_enforces_step_limit(tmp_path: Path):
    workflow = sample_workflow()
    workflow["max_steps"] = 2
    state_path = tmp_path / "run.json"
    state = initialize_run(state_path, sample_case(), sample_approach(), workflow)
    state = record_proposal(state_path, state, workflow, "need-evidence", "Important fact is unknown.", "It may change the outcome.")
    state = record_proposal(state_path, state, workflow, "respond-after-review", "Status is still being verified.", "The response requires review.")
    state = reject_route(state_path, state, workflow, "respond-after-review", "The current evidence is incomplete.")

    with pytest.raises(WorkflowError, match="step limit"):
        record_proposal(state_path, state, workflow, "respond-after-review", "Status is confirmed.", "The response is now supported.")

    state = extend_run(state_path, state, workflow, 3, "One more evidence-led transition is needed to finish.")
    state = record_proposal(state_path, state, workflow, "respond-after-review", "Status is confirmed.", "The response is now supported.")
    state = approve_route(state_path, state, workflow, "respond-after-review")
    assert state["current_phase"] == "respond"
    assert state["step"] == 3


def test_workflow_validation_rejects_budget_below_shortest_completion():
    workflow = sample_workflow()
    workflow["max_steps"] = 1

    errors = validate_workflow(workflow, sample_approach())

    assert any("at least 2 transitions" in error for error in errors)


def test_stale_snapshot_cannot_overwrite_a_newer_transition(tmp_path: Path):
    state_path = tmp_path / "run.json"
    workflow = sample_workflow()
    initialize_run(state_path, sample_case(), sample_approach(), workflow)
    first = load_run(state_path, workflow, sample_approach())
    stale = load_run(state_path, workflow, sample_approach())

    record_proposal(state_path, first, workflow, "need-evidence", "Status is unknown.", "A key fact remains open.")
    with pytest.raises(WorkflowError, match="changed since it was read"):
        record_proposal(state_path, stale, workflow, "ready-to-respond", "Current facts are sufficient.", "No investigation is needed.")

    current = load_run(state_path, workflow, sample_approach())
    assert current["current_phase"] == "investigate"
    assert len(current["events"]) == 1


def test_locked_run_rejects_a_second_writer(tmp_path: Path):
    from mythopraxis.workflows import _run_lock

    state_path = tmp_path / "run.json"
    workflow = sample_workflow()
    state = initialize_run(state_path, sample_case(), sample_approach(), workflow)

    with _run_lock(state_path):
        with pytest.raises(WorkflowError, match="locked for update"):
            record_proposal(state_path, state, workflow, "need-evidence", "Status is unknown.", "A key fact remains open.")

    state = record_proposal(state_path, state, workflow, "need-evidence", "Status is unknown.", "A key fact remains open.")
    assert state["current_phase"] == "investigate"


def test_repository_validation_reports_non_mapping_workflow(tmp_path: Path):
    source = Path(__file__).resolve().parents[1]
    root = tmp_path / "repository"
    shutil.copytree(source, root, ignore=shutil.ignore_patterns(".git", "audit-venv", "__pycache__", "*.pyc"))
    (root / "workflows" / "examples" / "bad.yaml").write_text("[]", encoding="utf-8")

    errors = validate_repository(root)

    assert any("bad.yaml: workflow must be a mapping" in error for error in errors)


def test_orchestrate_cli_starts_and_emits_phase_packet(tmp_path: Path, capsys):
    case_path, approach_path, workflow_path = create_inputs(tmp_path)
    state_path = tmp_path / "state.json"

    assert main(["orchestrate", "start", "--case", str(case_path), "--approach", str(approach_path), "--workflow", str(workflow_path), "--state", str(state_path)]) == 0
    assert "Run started" in capsys.readouterr().out
    assert main(["orchestrate", "next", "--case", str(case_path), "--approach", str(approach_path), "--workflow", str(workflow_path), "--state", str(state_path)]) == 0
    output = capsys.readouterr().out
    assert "## Current phase" in output
    assert "need-evidence" in output
    assert "no provider calls" in output
    assert main(["orchestrate", "record", "--approach", str(approach_path), "--workflow", str(workflow_path), "--state", str(state_path), "--route", "need-evidence", "--evidence", "Settlement status is not yet known.", "--rationale", "That fact could change the safe next step."]) == 0
    assert json.loads(state_path.read_text(encoding="utf-8"))["current_phase"] == "investigate"
