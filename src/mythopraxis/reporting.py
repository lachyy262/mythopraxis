"""Generate evidence-bounded Markdown reports from evaluation results."""

import json
import html
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from mythopraxis.contracts import load_contract, validate_instance
from mythopraxis.inputs import HARD_MAX_RUNS, MAX_INPUT_BYTES


MAX_REPORT_BYTES = 16 * MAX_INPUT_BYTES


def _run_key(row: dict[str, Any]) -> tuple:
    return tuple(row[key] for key in (
        "model", "harness_version", "condition", "scenario", "seed"
    ))


def _cell(value: str) -> str:
    """Keep labels as literal, single-line Markdown text."""
    text = html.escape(" ".join(value.split()), quote=False)
    return re.sub(r"([\\|`*\[\]_#!])", r"\\\1", text)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("nonfinite JSON number")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Validate all records before reporting; never echo raw response data in errors."""
    if not path.is_file():
        raise ValueError("results input must be a regular file")
    schema = load_contract("eval-result.schema.json")
    rows = []
    judgments = set()
    outputs = {}
    total_bytes = 0
    with path.open("rb") as stream:
        number = 0
        while raw := stream.readline(MAX_INPUT_BYTES + 1):
            number += 1
            total_bytes += len(raw)
            prefix = f"line {number}: "
            if len(raw) > MAX_INPUT_BYTES or total_bytes > MAX_REPORT_BYTES:
                raise ValueError(prefix + "results exceed the input byte limit")
            if not raw.strip():
                continue
            if len(rows) >= HARD_MAX_RUNS:
                raise ValueError(prefix + f"results exceed {HARD_MAX_RUNS} records")
            try:
                row = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                                 parse_constant=_reject_constant)
                errors = validate_instance(row, schema)
            except (ValueError, RecursionError) as error:
                raise ValueError(prefix + "invalid JSON evaluation record") from error
            if errors:
                raise ValueError(prefix + "invalid evaluation record (schema mismatch)")
            if row["judge_type"] == "unscored" and row["rubric_scores"]:
                raise ValueError(prefix + "unscored records cannot contain scores")
            identity = _run_key(row)
            judgment = (*identity, row["judge_type"])
            if judgment in judgments:
                raise ValueError(prefix + "duplicate judgment for the same run")
            if identity in outputs and outputs[identity] != row["response"]:
                raise ValueError(prefix + "conflicting responses for the same run")
            judgments.add(judgment)
            outputs[identity] = row["response"]
            rows.append(row)
    return rows


def _score_sections(rows: list[dict[str, Any]]) -> list[str]:
    scopes = defaultdict(list)
    for row in rows:
        if row["judge_type"] != "unscored":
            scopes[(row["model"], row["harness_version"], row["judge_type"])].append(row)
    lines = []
    for scope, records in sorted(scopes.items()):
        groups = defaultdict(list)
        for row in records:
            groups[(row["scenario"], row["condition"])].append(row)
        if not any(row["rubric_scores"] for row in records):
            continue
        lines.extend([
            "", "### " + " / ".join(_cell(value) for value in scope), "",
            "| Scenario | Condition | Dimension | Scored / records | Mean (1–5) |",
            "|---|---|---|---|---|",
        ])
        for (scenario, condition), group in sorted(groups.items()):
            dimensions = sorted({key for row in group for key in row["rubric_scores"]})
            for dimension in dimensions:
                scores = [row["rubric_scores"][dimension] for row in group
                          if dimension in row["rubric_scores"]]
                lines.append(
                    f"| {_cell(scenario)} | {_cell(condition)} | {_cell(dimension)} | "
                    f"{len(scores)}/{len(group)} | {mean(scores):.2f} |"
                )
    return lines


def render_report(path: Path) -> str:
    """Render a descriptive report without inferring unsupported effects."""
    rows = _read_jsonl(path)
    scored = [row for row in rows if row.get("rubric_scores")]
    lines = [
        "# Mythopraxis Evaluation Report",
        "",
        "> Directional pilot only. This report is not a statistical conclusion.",
        "",
        f"Records loaded: {len(rows)}",
        f"Unique model outputs: {len({_run_key(row) for row in rows})}",
        f"Unscored records: {sum(row['judge_type'] == 'unscored' for row in rows)}",
        "",
    ]
    if not scored:
        lines.append("No scored conclusions are available. Results remain descriptive artifacts.")
    else:
        lines.append("Scores are reported by condition without causal interpretation.")
        lines.append("Missing scores are not zeros. Models, harness versions, scenarios, and judge types are not pooled; no composite score or winning method is calculated.")
        lines.extend(_score_sections(rows))
    return "\n".join(lines) + "\n"
