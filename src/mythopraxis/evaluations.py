"""Build deterministic evaluation run matrices."""

from itertools import product
from typing import Any


def expand_matrix(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand conditions, scenarios, models, and repeat seeds into runs."""
    models = matrix.get("models")
    if not models:
        raise ValueError("models must be supplied explicitly")
    conditions = matrix.get("conditions", [])
    scenarios = matrix.get("scenarios", [])
    repeats = int(matrix.get("repeats", 0))
    if not conditions or not scenarios or repeats < 1:
        raise ValueError("conditions, scenarios, and a positive repeats value are required")
    return [
        {"condition": condition, "scenario": scenario, "model": model, "seed": seed}
        for condition, scenario, model, seed in product(
            conditions, scenarios, models, range(1, repeats + 1)
        )
    ]
