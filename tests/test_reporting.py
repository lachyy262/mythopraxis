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
