"""Lazy provider adapters for explicitly authorized live evaluations."""


def call_provider(model: str, prompt: str, seed: int) -> str:
    """Call the provider named by a `provider:model-id` string."""
    del seed
    try:
        provider, model_id = model.split(":", 1)
    except ValueError as error:
        raise ValueError("model must use provider:model-id syntax") from error
    if provider == "openai":
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError("install mythopraxis[providers] to run OpenAI evaluations") from error
        response = OpenAI().responses.create(model=model_id, input=prompt)
        return response.output_text
    if provider == "anthropic":
        try:
            from anthropic import Anthropic
        except ImportError as error:
            raise RuntimeError("install mythopraxis[providers] to run Anthropic evaluations") from error
        response = Anthropic().messages.create(
            model=model_id,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    raise ValueError(f"unknown provider: {provider}")
