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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
