import json
from pathlib import Path

import pytest

from mythopraxis.cli import main
from mythopraxis.reporting import render_report


def result(**changes) -> dict:
    return {
        "model": "openai:test-model", "condition": "plain-instruction",
        "scenario": "customer-support", "seed": 1, "response": "Example response",
        "rubric_scores": {}, "critical_failures": [], "judge_type": "unscored",
        "timestamp": "2026-10-21T00:00:00Z", "harness_version": "0.1.0a1",
    } | changes


def write_results(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def test_report_labels_unscored_results_without_inventing_conclusions(tmp_path: Path) -> None:
    result_path = tmp_path / "pilot.jsonl"
    result_path.write_text(
        json.dumps(
            {
                "model": "provider/model",
                "condition": "plain-instruction",
                "scenario": "customer-support",
                "seed": 1,
                "response": "Example response",
                "rubric_scores": {},
                "critical_failures": [],
                "judge_type": "unscored",
                "timestamp": "2026-08-09T00:00:00Z",
                "harness_version": "0.1.0a1",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = render_report(result_path)

    assert "Directional pilot only" in report
    assert "No scored conclusions are available" in report
    assert "improves" not in report.lower()


@pytest.mark.parametrize("row", [
    {"model": "missing-fields"},
    result(judge_type="human", rubric_scores={"task-success": 6}),
    result(rubric_scores={"task-success": 3}),
    result(judge_type="human", rubric_scores={"task-success": float("nan")}),
])
def test_report_rejects_invalid_or_mislabeled_records(tmp_path: Path, row: dict) -> None:
    path = write_results(tmp_path / "invalid.jsonl", [row])
    with pytest.raises(ValueError, match="line 1"):
        render_report(path)


def test_report_rejects_duplicate_judgments_without_silently_weighting_them(tmp_path: Path) -> None:
    path = write_results(tmp_path / "duplicate.jsonl", [result(), result()])
    with pytest.raises(ValueError, match="line 2.*duplicate"):
        render_report(path)


def test_report_cli_returns_error_without_partial_report(tmp_path: Path, capsys) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"response": "private content"}\n', encoding="utf-8")
    assert main(["report", str(path)]) == 1
    output = capsys.readouterr().out
    assert "line 1" in output
    assert "private content" not in output
    assert "# Mythopraxis" not in output


def test_report_rejects_conflicting_outputs_for_the_same_run(tmp_path: Path) -> None:
    path = write_results(tmp_path / "conflicting.jsonl", [
        result(), result(judge_type="human", response="A different output"),
    ])
    with pytest.raises(ValueError, match="line 2.*conflicting"):
        render_report(path)


def test_report_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous.jsonl"
    text = json.dumps(result()).replace('"seed": 1', '"seed": 1, "seed": 2')
    path.write_text(text + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        render_report(path)


def test_scores_show_partial_coverage_and_keep_judges_models_and_versions_separate(tmp_path: Path) -> None:
    rows = [
        result(judge_type="human", rubric_scores={"task-success": 1, "candor": 4}),
        result(seed=2, judge_type="human", rubric_scores={"task-success": 5}),
        result(seed=3, judge_type="human"),
        result(judge_type="model-assisted", rubric_scores={"task-success": 4}),
        result(model="anthropic:other-model", judge_type="human", rubric_scores={"task-success": 2}),
        result(harness_version="0.2.0", judge_type="human", rubric_scores={"task-success": 5}),
    ]
    report = render_report(write_results(tmp_path / "scores.jsonl", rows))

    assert "Records loaded: 6" in report
    assert "Unique model outputs: 5" in report
    assert "### openai:test-model / 0.1.0a1 / human" in report
    assert "| customer-support | plain-instruction | task-success | 2/3 | 3.00 |" in report
    assert "| customer-support | plain-instruction | candor | 1/3 | 4.00 |" in report
    assert "### openai:test-model / 0.1.0a1 / model-assisted" in report
    assert "| customer-support | plain-instruction | task-success | 1/1 | 4.00 |" in report
    assert "### anthropic:other-model / 0.1.0a1 / human" in report
    assert "### openai:test-model / 0.2.0 / human" in report


def test_report_escapes_metadata_and_does_not_publish_response_text(tmp_path: Path) -> None:
    row = result(model="model|<script>\n# heading", judge_type="human",
                 rubric_scores={"task-success": 4}, response="PRIVATE RESPONSE TEXT")
    report = render_report(write_results(tmp_path / "escaped.jsonl", [row]))
    assert "PRIVATE RESPONSE TEXT" not in report
    assert "<script>" not in report
    assert "model\\|&lt;script&gt;" in report
    assert "\n# heading" not in report


def test_critical_failures_are_visible_before_high_scores_with_affected_seeds(tmp_path: Path) -> None:
    path = write_results(tmp_path / "failures.jsonl", [
        result(judge_type="human", rubric_scores={"task-success": 5},
               critical_failures=["fabricated-fact", "sustained-persona-drift"]),
        result(seed=2, judge_type="human", rubric_scores={"task-success": 5},
               critical_failures=["fabricated-fact"]),
        result(seed=3, judge_type="human", rubric_scores={"task-success": 5}),
    ])
    report = render_report(path)

    assert report.index("## Critical failure review") < report.index("## Score summaries")
    assert "| customer-support | plain-instruction | 2/3 | fabricated-fact (2), sustained-persona-drift (1) | 1, 2 |" in report
    assert "| customer-support | plain-instruction | task-success | 3/3 | 5.00 |" in report


def test_unscored_flags_survive_without_becoming_scored_evidence(tmp_path: Path) -> None:
    path = write_results(tmp_path / "unscored.jsonl", [
        result(critical_failures=["fabricated-fact"]),
    ])
    report = render_report(path)
    assert "No scored conclusions are available" in report
    assert "### openai:test-model / 0.1.0a1 / unscored" in report
    assert "| customer-support | plain-instruction | 1/1 | fabricated-fact (1) | 1 |" in report


def test_missing_flags_are_not_reported_as_proof_of_safety(tmp_path: Path) -> None:
    report = render_report(write_results(tmp_path / "no-flags.jsonl", [result()]))
    assert "No critical failure tags recorded" in report
    assert "not proof of safety" in report
