import json
from pathlib import Path

from mythopraxis.runner import resolve_model_placeholders, run_evaluations


def test_resolve_model_placeholders_requires_environment(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    try:
        resolve_model_placeholders(["${OPENAI_MODEL}"])
    except ValueError as error:
        assert "OPENAI_MODEL" in str(error)
    else:
        raise AssertionError("unresolved model placeholder must be rejected")


def test_run_evaluations_writes_unscored_jsonl(tmp_path: Path) -> None:
    runs = [{"model": "openai:test", "condition": "plain", "scenario": "support", "seed": 1}]

    def prompt_factory(run: dict[str, object]) -> str:
        return f"Prompt for {run['scenario']}"

    def provider(model: str, prompt: str, seed: int) -> str:
        assert model == "openai:test"
        assert prompt == "Prompt for support"
        assert seed == 1
        return "A measured response"

    output = tmp_path / "pilot.jsonl"
    count = run_evaluations(runs, prompt_factory, provider, output)

    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert count == 1
    assert records[0]["response"] == "A measured response"
    assert records[0]["judge_type"] == "unscored"
    assert records[0]["rubric_scores"] == {}
