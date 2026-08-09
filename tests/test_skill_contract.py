from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "mythopraxis" / "SKILL.md"


def test_skill_teaches_all_three_modes_and_bounded_rehearsal() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "TODO" not in text
    assert "## Weave" in text
    assert "## Apply" in text
    assert "## Audit" in text
    assert "bounded first-person rehearsal" in text.lower()
    assert "return fully as the Assistant" in text


def test_skill_description_is_trigger_focused() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "description: Use when" in text
    assert "customer support" in text.lower()
    assert "debugging" in text.lower()
    assert "code review" in text.lower()
