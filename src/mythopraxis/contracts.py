"""Trusted, packaged contracts with offline JSON Schema reference resolution."""
import json
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry
from referencing.exceptions import Unresolvable


def load_contract(name: str) -> dict[str, Any]:
    """Load a contract shipped with the installed harness, not the input tree."""
    return json.loads(files("mythopraxis").joinpath("schemas", name).read_text(encoding="utf-8"))


def validate_instance(instance: Any, schema: dict[str, Any]) -> list[str]:
    """Validate offline; unknown references fail closed without retrieving them."""
    try:
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker(), registry=Registry())
        return sorted(error.message for error in validator.iter_errors(instance))
    except Unresolvable:
        return ["schema references an unavailable resource; external retrieval is disabled"]
    except (SchemaError, RecursionError):
        return ["invalid or excessively nested schema or document"]
