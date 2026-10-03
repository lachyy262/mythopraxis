"""Command-line interface for the Mythopraxis harness."""

import argparse
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Sequence

from uuid import uuid4

from mythopraxis.approaches import (
    compose_approach,
    initialize_approach,
    load_approach,
)
from mythopraxis.workflows import (
    WorkflowError,
    approve_route,
    extend_run,
    initialize_run,
    load_run,
    load_workflow,
    phase_packet,
    record_proposal,
    reject_route,
    select_route,
)
from mythopraxis.cases import authoring_brief, initialize_case, load_case
from mythopraxis.inputs import DEFAULT_MAX_RUNS, load_yaml

from mythopraxis.evaluations import expand_matrix
from mythopraxis.interventions import load_intervention
from mythopraxis.prompts import build_prompt
from mythopraxis.providers import call_provider
from mythopraxis.rendering import render_intervention
from mythopraxis.reporting import render_report
from mythopraxis.runner import resolve_model_placeholders, run_evaluations
from mythopraxis.validation import validate_repository


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mythopraxis")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate repository content")
    validate.add_argument("path", nargs="?", default=".")

    render = subparsers.add_parser("render", help="render an intervention for a task")
    render.add_argument("intervention")
    render.add_argument("--task", required=True)

    evaluate = subparsers.add_parser("eval", help="expand or execute an evaluation matrix")
    evaluate.add_argument("--matrix", required=True)
    evaluate.add_argument("--dry-run", action="store_true")
    evaluate.add_argument("--output")
    evaluate.add_argument("--max-runs", type=int, default=DEFAULT_MAX_RUNS, help="maximum permitted runs (1-10000; default 1000)")

    report = subparsers.add_parser("report", help="render a Markdown results report")
    report.add_argument("results")

    case = subparsers.add_parser("case", help="create and validate context for authoring")
    case_commands = case.add_subparsers(dest="case_command", required=True)
    case_init = case_commands.add_parser("init", help="write a private starter case")
    case_init.add_argument("path")
    case_validate = case_commands.add_parser("validate", help="validate case context")
    case_validate.add_argument("path")
    case_brief = case_commands.add_parser("brief", help="export an agent authoring brief")
    case_brief.add_argument("path")

    approach = subparsers.add_parser(
        "approach", help="create and validate reusable work approaches"
    )
    approach_commands = approach.add_subparsers(dest="approach_command", required=True)
    approach_init = approach_commands.add_parser(
        "init", help="write a private starter approach"
    )
    approach_init.add_argument("path")
    approach_validate = approach_commands.add_parser(
        "validate", help="validate a work approach"
    )
    approach_validate.add_argument("path")

    compose = subparsers.add_parser("compose", help="compose a case with one approach phase")
    compose.add_argument("--case", required=True)
    compose.add_argument("--approach", required=True)
    compose.add_argument("--phase", required=True)

    orchestrate = subparsers.add_parser("orchestrate", help="run an adaptive, human-visible workflow")
    orchestration_commands = orchestrate.add_subparsers(dest="orchestration_command", required=True)
    workflow_validate = orchestration_commands.add_parser("validate", help="validate a workflow against an approach")
    workflow_validate.add_argument("--workflow", required=True)
    workflow_validate.add_argument("--approach", required=True)
    for name, help_text in (("start", "start a private workflow trace"), ("next", "compose the current phase packet")):
        command = orchestration_commands.add_parser(name, help=help_text)
        command.add_argument("--case", required=True)
        command.add_argument("--approach", required=True)
        command.add_argument("--workflow", required=True)
        command.add_argument("--state", required=True)
    record = orchestration_commands.add_parser("record", help="record a route proposal or pause")
    record.add_argument("--workflow", required=True)
    record.add_argument("--approach", required=True)
    record.add_argument("--state", required=True)
    record.add_argument("--route")
    record.add_argument("--evidence", required=True)
    record.add_argument("--rationale", required=True)
    record.add_argument("--pause", action="store_true")
    approve = orchestration_commands.add_parser("approve", help="approve a route that requires a person")
    approve.add_argument("--workflow", required=True)
    approve.add_argument("--approach", required=True)
    approve.add_argument("--state", required=True)
    approve.add_argument("--route", required=True)
    reject = orchestration_commands.add_parser("reject", help="reject a gated route and return for reconsideration")
    reject.add_argument("--workflow", required=True)
    reject.add_argument("--approach", required=True)
    reject.add_argument("--state", required=True)
    reject.add_argument("--route", required=True)
    reject.add_argument("--rationale", required=True)
    extend = orchestration_commands.add_parser("extend", help="let an author increase the run step budget")
    extend.add_argument("--workflow", required=True)
    extend.add_argument("--approach", required=True)
    extend.add_argument("--state", required=True)
    extend.add_argument("--steps", type=int, required=True, help="new total step limit (maximum 100)")
    extend.add_argument("--rationale", required=True)
    select = orchestration_commands.add_parser("select", help="resolve a no-match pause as workflow author")
    select.add_argument("--workflow", required=True)
    select.add_argument("--approach", required=True)
    select.add_argument("--state", required=True)
    select.add_argument("--route", required=True)
    select.add_argument("--rationale", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface and return a process exit code."""
    args = _parser().parse_args(argv)
    if args.command == "validate":
        errors = validate_repository(Path(args.path).resolve())
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print("Repository contract valid")
        return 0
    if args.command == "render":
        intervention = load_intervention(Path(args.intervention))
        print(render_intervention(intervention, args.task), end="")
        return 0
    if args.command == "eval":
        matrix_path = Path(args.matrix).resolve()
        matrix = load_yaml(matrix_path)
        runs = expand_matrix(matrix, max_runs=args.max_runs)
        if args.dry_run:
            print(f"Expanded {len(runs)} runs. No provider calls were made.")
            return 0
        resolved_models = resolve_model_placeholders(matrix["models"])
        for run in runs:
            run["model"] = resolved_models[matrix["models"].index(run["model"])]
        root = matrix_path.parent.parent
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = Path(args.output).absolute() if args.output else root / "evals" / "results" / f"pilot-{stamp}-{uuid4().hex}.jsonl"
        count = run_evaluations(runs, partial(build_prompt, root), call_provider, output, max_runs=args.max_runs)
        print(f"Wrote {count} unscored runs to {output}")
        return 0
    if args.command == "report":
        print(render_report(Path(args.results)), end="")
        return 0
    if args.command == "case":
        path = Path(args.path).expanduser()
        if args.case_command == "init":
            try:
                initialize_case(path)
            except FileExistsError:
                print(f"ERROR: refusing to overwrite existing case: {path}")
                return 1
            print(f"Created private case template: {path}")
            return 0
        try:
            case = load_case(path)
        except (OSError, ValueError) as error:
            print(f"ERROR: {error}")
            return 1
        if args.case_command == "validate":
            print(f"Case valid: {case['id']}")
            return 0
        print(authoring_brief(case), end="")
        return 0
    if args.command == "approach":
        path = Path(args.path).expanduser()
        if args.approach_command == "init":
            try:
                initialize_approach(path)
            except FileExistsError:
                print(f"ERROR: refusing to overwrite existing approach: {path}")
                return 1
            print(f"Created private approach template: {path}")
            return 0
        try:
            approach = load_approach(path)
        except (OSError, ValueError) as error:
            print(f"ERROR: {error}")
            return 1
        print(f"Approach valid: {approach['id']}")
        return 0
    if args.command == "compose":
        try:
            case = load_case(Path(args.case).expanduser())
            approach = load_approach(Path(args.approach).expanduser())
            packet = compose_approach(case, approach, args.phase)
        except (OSError, ValueError) as error:
            print(f"ERROR: {error}")
            return 1
        print(packet, end="")
        return 0
    if args.command == "orchestrate":
        try:
            if args.orchestration_command == "validate":
                approach = load_approach(Path(args.approach).expanduser())
                workflow = load_workflow(Path(args.workflow).expanduser(), approach)
                print(f"Workflow valid: {workflow['id']}")
                return 0
            if args.orchestration_command == "start":
                case = load_case(Path(args.case).expanduser())
                approach = load_approach(Path(args.approach).expanduser())
                workflow = load_workflow(Path(args.workflow).expanduser(), approach)
                state = initialize_run(Path(args.state), case, approach, workflow)
                print(f"Run started: {state['run_id']} at phase {state['current_phase']}")
                return 0
            workflow_path = Path(args.workflow).expanduser()
            approach = load_approach(Path(args.approach).expanduser())
            workflow = load_workflow(workflow_path, approach)
            state = load_run(Path(args.state), workflow, approach)
            if args.orchestration_command == "next":
                case = load_case(Path(args.case).expanduser())
                print(phase_packet(case, approach, workflow, state), end="")
                return 0
            if args.orchestration_command == "record":
                state = record_proposal(Path(args.state), state, workflow, args.route, args.evidence, args.rationale, pause=args.pause)
            elif args.orchestration_command == "approve":
                state = approve_route(Path(args.state), state, workflow, args.route)
            elif args.orchestration_command == "reject":
                state = reject_route(Path(args.state), state, workflow, args.route, args.rationale)
            elif args.orchestration_command == "extend":
                state = extend_run(Path(args.state), state, workflow, args.steps, args.rationale)
            elif args.orchestration_command == "select":
                state = select_route(Path(args.state), state, workflow, args.route, args.rationale)
            print(f"Run {state['status']}: phase {state['current_phase']}, step {state['step']}")
            return 0
        except (OSError, ValueError) as error:
            print(f"ERROR: {error}")
            return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
