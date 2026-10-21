"""Generate evidence-bounded Markdown reports from evaluation results."""

import json
import html
import re
from collections import Counter, defaultdict
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


def _failure_sections(rows: list[dict[str, Any]]) -> list[str]:
    lines = ["## Critical failure review", ""]
    if not any(row["critical_failures"] for row in rows):
        return lines + ["No critical failure tags recorded; absence of flags is not proof of safety.", ""]
    lines.extend([
        "Recorded flags require review even when scores are high. Flagged records remain in score summaries. Tags are annotations, not independently verified findings; unscored flags have no attributed judge.", "",
    ])
    scopes = defaultdict(list)
    for row in rows:
        scopes[(row["model"], row["harness_version"], row["judge_type"])].append(row)
    for scope, records in sorted(scopes.items()):
        if not any(row["critical_failures"] for row in records):
            continue
        lines.extend([
            "### " + " / ".join(_cell(value) for value in scope), "",
            "| Scenario | Condition | Flagged / records | Tags (record counts) | Affected seeds |",
            "|---|---|---|---|---|",
        ])
        groups = defaultdict(list)
        for row in records:
            groups[(row["scenario"], row["condition"])].append(row)
        for (scenario, condition), group in sorted(groups.items()):
            flagged = [row for row in group if row["critical_failures"]]
            if not flagged:
                continue
            counts = Counter(tag for row in flagged for tag in row["critical_failures"])
            tags = ", ".join(f"{_cell(tag)} ({count})" for tag, count in sorted(counts.items()))
            seeds = ", ".join(str(row["seed"]) for row in sorted(flagged, key=lambda row: row["seed"]))
            lines.append(f"| {_cell(scenario)} | {_cell(condition)} | {len(flagged)}/{len(group)} | {tags} | {seeds} |")
        lines.append("")
    return lines


def _comparison_sections(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "", "## Matched comparisons with plain instructions", "",
        "Pair only within the same model, harness version, judge type, scenario, seed, and scored dimension. Delta is condition minus plain-instruction on those pairs. Unmatched counts refer to scored records for that dimension; missing values are never zeros.", "",
        "Matching identifiers is not proof of a controlled experiment. Verify common prompts, model settings, rubric, and evaluation batch externally. Seeds identify repeats and do not guarantee deterministic or equivalent sampling. Deltas are descriptive, not causal effects or significance tests.", "",
    ]
    scopes = defaultdict(list)
    for row in rows:
        if row["judge_type"] != "unscored":
            scopes[(row["model"], row["harness_version"], row["judge_type"])].append(row)
    alternatives = 0
    for scope, records in sorted(scopes.items()):
        groups = defaultdict(dict)
        for row in records:
            groups[(row["scenario"], row["condition"])][row["seed"]] = row["rubric_scores"]
        entries = []
        for (scenario, condition), scores_by_seed in sorted(groups.items()):
            if condition == "plain-instruction":
                continue
            baseline = groups.get((scenario, "plain-instruction"), {})
            dimensions = sorted({key for scores in [*scores_by_seed.values(), *baseline.values()] for key in scores})
            for dimension in dimensions:
                candidate_scores = {seed: scores[dimension] for seed, scores in scores_by_seed.items() if dimension in scores}
                baseline_scores = {seed: scores[dimension] for seed, scores in baseline.items() if dimension in scores}
                pairs = candidate_scores.keys() & baseline_scores.keys()
                delta = mean(candidate_scores[seed] - baseline_scores[seed] for seed in sorted(pairs)) if pairs else None
                displayed = f"{delta:+.2f}" if delta is not None else "n/a"
                entries.append(
                    f"| {_cell(scenario)} | {_cell(condition)} | {_cell(dimension)} | {len(pairs)} | "
                    f"{len(candidate_scores) - len(pairs)} | {len(baseline_scores) - len(pairs)} | {displayed} |"
                )
        if entries:
            alternatives += len(entries)
            lines.extend([
                "### " + " / ".join(_cell(value) for value in scope), "",
                "| Scenario | Condition | Dimension | Pairs | Condition unmatched | Baseline unmatched | Mean delta |",
                "|---|---|---|---|---|---|---|", *entries, "",
            ])
    if not alternatives:
        lines.append("No alternative-condition scores or matching baseline dimensions are available for comparison.")
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
    lines.extend(_failure_sections(rows))
    if not scored:
        lines.append("No scored conclusions are available. Results remain descriptive artifacts.")
    else:
        lines.extend(["## Score summaries", ""])
        lines.append("Scores are reported by condition without causal interpretation.")
        lines.append("Missing scores are not zeros. Models, harness versions, scenarios, and judge types are not pooled; no composite score or winning method is calculated.")
        lines.extend(_score_sections(rows))
        lines.extend(_comparison_sections(rows))
    return "\n".join(lines) + "\n"
