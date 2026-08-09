"""Execute explicitly authorized evaluation runs."""

import json
import os
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mythopraxis import __version__


PromptFactory = Callable[[dict[str, Any]], str]
Provider = Callable[[str, str, int], str]


def resolve_model_placeholders(models: Iterable[str]) -> list[str]:
    """Resolve exact ${NAME} model placeholders from the environment."""
    resolved: list[str] = []
    for model in models:
        if model.startswith("${") and model.endswith("}"):
            name = model[2:-1]
            value = os.environ.get(name)
            if not value:
                raise ValueError(f"environment variable {name} is required for a live run")
            resolved.append(value)
        else:
            resolved.append(model)
    return resolved


def run_evaluations(
    runs: Iterable[dict[str, Any]],
    prompt_factory: PromptFactory,
    provider: Provider,
    output_path: Path,
) -> int:
    """Execute runs and append unscored, provenance-rich JSONL records."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        for run in runs:
            response = provider(str(run["model"]), prompt_factory(run), int(run["seed"]))
            record = {
                "model": run["model"],
                "condition": run["condition"],
                "scenario": run["scenario"],
                "seed": run["seed"],
                "response": response,
                "rubric_scores": {},
                "critical_failures": [],
                "judge_type": "unscored",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "harness_version": __version__,
            }
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            count += 1
    return count
