from pathlib import Path

from mythopraxis.cli import main


ROOT = Path(__file__).resolve().parents[1]


def test_eval_dry_run_reports_expanded_count(capsys) -> None:
    exit_code = main(["eval", "--matrix", str(ROOT / "evals" / "matrix.yaml"), "--dry-run"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "180 runs" in captured.out
    assert "No provider calls were made" in captured.out


def test_validate_returns_zero_for_complete_repository(capsys) -> None:
    exit_code = main(["validate", str(ROOT)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Repository contract valid" in captured.out
