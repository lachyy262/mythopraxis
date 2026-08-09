from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_repository_documents_are_present() -> None:
    required = [
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "PROVENANCE.md",
        "CITATION.cff",
        "CHANGELOG.md",
    ]
    assert [name for name in required if not (ROOT / name).exists()] == []


def test_ci_never_runs_live_evaluations() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "--dry-run" in workflow
    assert "OPENAI_API_KEY" not in workflow
    assert "ANTHROPIC_API_KEY" not in workflow
