"""Execute bounded evaluations after validating every prompt."""
import json
import os
import re
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path
from typing import Any

from mythopraxis import __version__
from mythopraxis.inputs import (
    DEFAULT_MAX_RUNS, MAX_PROMPT_CHARS, MAX_TOTAL_PROMPT_CHARS,
    create_private_parents, validate_run_limit,
)

PromptFactory = Callable[[dict[str, Any]], str]
Provider = Callable[[str, str, int], str]
MODEL_ENV_NAMES = {"OPENAI_MODEL", "ANTHROPIC_MODEL"}


def validate_model(model: str) -> None:
    """Accept configured providers and bounded model IDs before any side effects."""
    if not isinstance(model, str) or not re.fullmatch(r"(?:openai|anthropic):[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", model):
        raise ValueError("model must use openai:model-id or anthropic:model-id syntax")


def resolve_model_placeholders(models: Iterable[str]) -> list[str]:
    resolved = []
    for model in models:
        if isinstance(model, str) and model.startswith("${") and model.endswith("}"):
            name = model[2:-1]
            if name not in MODEL_ENV_NAMES:
                raise ValueError("only OPENAI_MODEL and ANTHROPIC_MODEL placeholders are allowed")
            model = os.environ.get(name)
            if not model:
                raise ValueError(f"environment variable {name} is required for a live run")
        validate_model(model)
        resolved.append(model)
    return resolved


def run_evaluations(
    runs: Iterable[dict[str, Any]],
    prompt_factory: PromptFactory,
    provider: Provider,
    output_path: Path,
    max_runs: int = DEFAULT_MAX_RUNS,
) -> int:
    """Preflight bounded inputs, then create a private, exclusive results file."""
    validate_run_limit(max_runs)
    bounded = list(islice(runs, max_runs + 1))
    if not bounded or len(bounded) > max_runs:
        raise ValueError(f"evaluation requires between 1 and {max_runs} runs")
    prepared = []
    total_chars = 0
    for run in bounded:
        if not isinstance(run, dict):
            raise ValueError("each run must be a mapping")
        for field in ("condition", "scenario"):
            value = run.get(field)
            if not isinstance(value, str) or not value.strip() or len(value) > 255:
                raise ValueError(f"run {field} must contain 1 to 255 characters")
        validate_model(run.get("model"))
        if type(run.get("seed")) is not int or run["seed"] < 1:
            raise ValueError("seed must be a positive integer")
        prompt = prompt_factory(run)
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT_CHARS:
            raise ValueError(f"prompt must contain 1 to {MAX_PROMPT_CHARS} characters")
        total_chars += len(prompt)
        if total_chars > MAX_TOTAL_PROMPT_CHARS:
            raise ValueError(f"combined prompts exceed {MAX_TOTAL_PROMPT_CHARS} characters")
        prepared.append((dict(run), prompt))
    create_private_parents(output_path.parent)
    # O_EXCL rejects existing regular files and symlinks atomically.
    fd = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    count = 0
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        for run, prompt in prepared:
            response = provider(run["model"], prompt, run["seed"])
            record = {
                "model": run["model"], "condition": run["condition"],
                "scenario": run["scenario"], "seed": run["seed"], "response": response,
                "rubric_scores": {}, "critical_failures": [], "judge_type": "unscored",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "harness_version": __version__,
            }
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            count += 1
    return count
