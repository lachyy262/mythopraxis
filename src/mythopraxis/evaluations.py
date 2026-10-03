"""Build deterministic, bounded evaluation run matrices."""
from itertools import product
from math import prod
from typing import Any

from mythopraxis.inputs import DEFAULT_MAX_RUNS, SLUG, validate_run_limit

CONDITIONS = {
    "plain-instruction", "generic-expert-persona", "sustained-story-persona",
    "anchored-third-person-witness", "bounded-first-person-rehearsal",
}


def expand_matrix(matrix: dict[str, Any], max_runs: int = DEFAULT_MAX_RUNS) -> list[dict[str, Any]]:
    """Validate and cap the Cartesian product before allocating any runs."""
    validate_run_limit(max_runs)
    if not isinstance(matrix, dict):
        raise ValueError("matrix must be a mapping")
    axes = []
    for name in ("conditions", "scenarios", "models"):
        values = matrix.get(name)
        if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError(f"{name} must be supplied explicitly as a nonempty string list")
        axes.append(values)
    conditions, scenarios, models = axes
    if any(c not in CONDITIONS for c in conditions):
        raise ValueError("unknown evaluation condition")
    if any(not SLUG.fullmatch(s) for s in scenarios):
        raise ValueError("scenario identifiers must be lowercase hyphenated slugs")
    repeats = matrix.get("repeats")
    if type(repeats) is not int or repeats < 1:
        raise ValueError("repeats must be a positive integer")
    count = prod(map(len, axes)) * repeats
    if count > max_runs:
        raise ValueError(f"matrix expands to {count} runs, exceeding the limit of {max_runs}")
    return [
        {"condition": condition, "scenario": scenario, "model": model, "seed": seed}
        for condition, scenario, model, seed in product(conditions, scenarios, models, range(1, repeats + 1))
    ]
