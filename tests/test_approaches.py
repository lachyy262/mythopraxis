import json
import os
from pathlib import Path

import pytest

from mythopraxis.approaches import (
    ApproachError,
    compose_approach,
    initialize_approach,
    load_approach,
    validate_approach,
)
from mythopraxis.cli import main


def sample_approach() -> dict:
    return {
        "approach_version": "1.0",
        "id": "investigate-and-respond",
        "title": "Investigate and Respond",
        "purpose": "Resolve uncertain requests with evidence and clear follow-through.",
        "when_to_use": ["The outcome depends on incomplete or changing evidence."],
        "phases": [
            {
                "id": "orient",
                "title": "Orient",
                "intent": "Understand the people, stakes, and outcome that matter.",
                "people_to_consider": ["Customer", "Operator"],
                "evidence_to_notice": ["What each person has already been told."],
                "tool_intents": ["Find the current state in authoritative records."],
                "decisions_to_surface": ["What information could change the next step?"],
                "progress_signals": ["The outcome and uncertainty are clear."],
                "posture_pair": ["curiosity", "respect"],
                "supporting_exemplars": ["lantern-bearer"],
            },
            {
                "id": "investigate",
                "title": "Investigate",
                "intent": "Use relevant evidence to narrow the available explanations.",
                "people_to_consider": ["Operator"],
                "evidence_to_notice": ["Source and freshness of each status."],
                "tool_intents": ["Check the source that owns the requested fact."],
                "decisions_to_surface": ["What is supported and what remains unknown?"],
                "progress_signals": ["The recommendation follows from verified facts."],
                "posture_pair": ["rigor", "humility"],
                "supporting_exemplars": ["honest-mirror"],
            },
            {
                "id": "respond",
                "title": "Respond",
                "intent": "Communicate the finding and establish useful follow-through.",
                "people_to_consider": ["Customer"],
                "evidence_to_notice": ["Any next update or escalation commitment."],
                "tool_intents": [],
                "decisions_to_surface": ["What can be promised with confidence?"],
                "progress_signals": ["The person knows the next step and its owner."],
                "posture_pair": ["candor", "care"],
                "supporting_exemplars": ["advocate-at-the-door"],
            },
        ],
    }


def sample_case() -> dict:
    return {
        "case_version": "1.0",
        "id": "transfer-delay",
        "purpose": "Resolve a delayed bank transfer with a useful follow-up.",
        "people": [
            {
                "id": "customer",
                "role": "account holder",
                "situation": "A transfer is later than the estimate.",
                "goals": ["Know where the funds are."],
                "stakes": ["A scheduled payment depends on the funds."],
                "expertise": "Knows their account, not settlement processing.",
                "needs_preferences": ["Plain facts and a next update."],
                "constraints": ["Cannot contact receiving bank today."],
            }
        ],
        "relationships": [],
        "work": {
            "outcome": "Explain verified status and agree a next update.",
            "stage": "Investigating a delayed transfer.",
            "process": ["Check status", "Explain options", "Follow up"],
            "tools": [
                {
                    "name": "status lookup",
                    "use": "Read the internal settlement status.",
                    "limits": "Cannot accelerate settlement.",
                }
            ],
        },
        "context": {
            "known": ["The estimated date has passed."],
            "unknown": ["Whether the receiving bank has posted the funds."],
            "assumptions": [],
        },
        "pressures": ["Pressure to reassure quickly."],
        "success": {
            "observable": ["Share verified facts", "Name the next update."],
            "avoid": ["Unsupported settlement promises."],
        },
        "boundaries": ["Follow payment policy."],
    }


def write_yaml(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_approach_requires_unique_ordered_phase_ids() -> None:
    approach = sample_approach()
    approach["phases"][1]["id"] = "orient"

    errors = validate_approach(approach)

    assert any("duplicate phase id orient" in error for error in errors)


def test_load_approach_rejects_non_mapping(tmp_path: Path) -> None:
    path = tmp_path / "approach.yaml"
    path.write_text("- not-an-approach", encoding="utf-8")

    with pytest.raises(ApproachError, match="mapping"):
        load_approach(path)


def test_initialize_approach_is_private_and_non_overwriting(tmp_path: Path) -> None:
    path = tmp_path / "private" / "approach.yaml"

    initialize_approach(path)

    assert load_approach(path)["id"] == "replace-me"
    if os.name == "posix":
        assert path.stat().st_mode & 0o777 == 0o600
        assert path.parent.stat().st_mode & 0o777 == 0o700
    path.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        initialize_approach(path)
    assert path.read_text(encoding="utf-8") == "keep"


def test_composition_expands_selected_phase_and_context_only(tmp_path: Path) -> None:
    case = sample_case()
    approach = sample_approach()

    prompt = compose_approach(case, approach, "investigate")

    assert "The estimated date has passed." in prompt
    assert "Cannot accelerate settlement." in prompt
    assert "Check the source that owns the requested fact." in prompt
    assert "## Approach outline" in prompt
    assert '"id": "orient"' in prompt
    assert "Find the current state in authoritative records." not in prompt
    assert "advocate-at-the-door" not in prompt
    assert "no provider calls" in prompt


def test_composition_requires_an_existing_phase() -> None:
    with pytest.raises(ApproachError, match="phase"):
        compose_approach(sample_case(), sample_approach(), "unknown")


def test_one_approach_adapts_to_a_different_case() -> None:
    case = sample_case()
    case["id"] = "release-review"
    case["purpose"] = "Help an engineer review a risky software release."
    case["people"][0]["role"] = "release engineer"
    case["people"][0]["situation"] = "A release is blocked by an uncertain test failure."
    case["people"][0]["goals"] = ["Ship only when the release risk is understood."]
    case["people"][0]["stakes"] = ["A faulty release could affect customers."]
    case["people"][0]["needs_preferences"] = ["A clear account of the remaining risk."]
    case["work"]["outcome"] = "Decide whether the release is safe to proceed."
    case["work"]["tools"][0]["name"] = "test dashboard"
    case["work"]["tools"][0]["use"] = "Read the latest automated test results."
    case["work"]["tools"][0]["limits"] = "Cannot determine business impact."
    case["context"]["known"] = ["A required test failed."]
    case["context"]["unknown"] = ["Whether the failure indicates a release-blocking defect."]

    prompt = compose_approach(case, sample_approach(), "investigate")

    assert "release engineer" in prompt
    assert "test dashboard" in prompt
    assert "Cannot determine business impact." in prompt
    assert "The estimated date has passed." not in prompt


def test_approach_cli_validates_and_composes(tmp_path: Path, capsys) -> None:
    approach_path = write_yaml(tmp_path / "approach.yaml", sample_approach())
    case_path = write_yaml(tmp_path / "case.yaml", sample_case())

    assert main(["approach", "validate", str(approach_path)]) == 0
    assert "Approach valid: investigate-and-respond" in capsys.readouterr().out

    assert main(
        [
            "compose",
            "--case",
            str(case_path),
            "--approach",
            str(approach_path),
            "--phase",
            "respond",
        ]
    ) == 0
    rendered = capsys.readouterr().out
    assert "## Current phase" in rendered
    assert "What can be promised with confidence?" in rendered


def test_approach_cli_init_writes_valid_template(tmp_path: Path, capsys) -> None:
    output = tmp_path / "approach.yaml"

    assert main(["approach", "init", str(output)]) == 0

    assert load_approach(output)["id"] == "replace-me"
    assert str(output) in capsys.readouterr().out
