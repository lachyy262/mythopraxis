from pathlib import Path

import json

from mythopraxis.validation import find_broken_local_links, validate_instance, validate_repository


ROOT = Path(__file__).resolve().parents[1]


def test_repository_contract_is_complete() -> None:
    assert validate_repository(ROOT) == []


def test_readme_has_required_opening_and_no_em_dash() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "The Stories Agents Carry" in readme
    assert "Shape how your agent responds when the easy answer stops working." in readme
    assert "Mythopraxis turns stories" in readme
    assert "\u2014" not in readme


def test_initial_library_contains_six_exemplars() -> None:
    exemplars = sorted((ROOT / "skills" / "mythopraxis" / "references" / "exemplars").glob("*.yaml"))
    assert len(exemplars) == 6


def test_schema_validation_reports_the_missing_field() -> None:
    schema = json.loads((ROOT / "schemas" / "intervention.schema.json").read_text(encoding="utf-8"))
    errors = validate_instance({"id": "incomplete"}, schema)

    assert any("exit_cue" in error for error in errors)


def test_readme_local_links_resolve() -> None:
    assert find_broken_local_links(ROOT / "README.md", ROOT) == []
