"""Load and validate narrative interventions."""

from pathlib import Path
from typing import Any

from mythopraxis.contracts import load_contract, validate_instance
from mythopraxis.inputs import load_yaml


class InterventionError(ValueError):
    """Raised when an intervention does not satisfy the core contract."""


REQUIRED_FIELDS = (
    "id",
    "title",
    "version",
    "purpose",
    "assistant_anchor",
    "scene",
    "tension",
    "choice",
    "postures",
    "covenant",
    "pressure_triggers",
    "recovery_cue",
    "exit_cue",
    "sources",
    "claims",
)


def load_intervention(path: Path) -> dict[str, Any]:
    """Load an intervention and enforce its bounded rehearsal contract."""
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise InterventionError("intervention must be a mapping")
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            raise InterventionError(f"{field} is required")
    errors = validate_instance(data, load_contract("intervention.schema.json"))
    if errors:
        raise InterventionError("; ".join(errors))
    return data
