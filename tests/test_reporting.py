import json
from pathlib import Path

from mythopraxis.reporting import render_report


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
