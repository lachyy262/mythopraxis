"""Command-line interface for the Mythopraxis harness."""

import argparse
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Sequence

from uuid import uuid4

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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
