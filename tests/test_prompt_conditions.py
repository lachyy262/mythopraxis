from pathlib import Path

from mythopraxis.prompts import build_prompt


ROOT = Path(__file__).resolve().parents[1]


def test_bounded_condition_returns_to_assistant_before_task() -> None:
    prompt = build_prompt(
        ROOT,
        {
            "condition": "bounded-first-person-rehearsal",
            "scenario": "incident-response",
            "model": "provider/model",
            "seed": 1,
        },
    )

    assert "Assistant anchor" in prompt
    assert "Leave the harbor and return fully as the Assistant" in prompt
    assert prompt.index("Exit the role") < prompt.index("Real task")


def test_sustained_condition_is_explicitly_marked_research_only() -> None:
    prompt = build_prompt(
        ROOT,
        {
            "condition": "sustained-story-persona",
            "scenario": "incident-response",
            "model": "provider/model",
            "seed": 1,
        },
    )

    assert "RESEARCH CONDITION" in prompt
    assert "Stay in character" in prompt
