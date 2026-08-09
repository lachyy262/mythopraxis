import sys
from types import SimpleNamespace

from mythopraxis.providers import call_provider


def test_openai_provider_is_loaded_lazily(monkeypatch) -> None:
    response = SimpleNamespace(output_text="provider response")
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: response))
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda: client))

    assert call_provider("openai:test-model", "hello", 7) == "provider response"


def test_unknown_provider_prefix_is_rejected() -> None:
    try:
        call_provider("unknown:model", "hello", 1)
    except ValueError as error:
        assert "unknown provider" in str(error)
    else:
        raise AssertionError("unknown provider must be rejected")
