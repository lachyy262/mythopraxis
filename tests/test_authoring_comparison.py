import json
import runpy
import shutil
from pathlib import Path

import pytest

from mythopraxis.cases import load_case
from mythopraxis.interventions import load_intervention


ROOT = Path(__file__).resolve().parents[1]


def builder():
    return runpy.run_path(str(ROOT / "evals/authoring/compare.py"))["build_comparison"]


@pytest.mark.parametrize("identifier", ["delayed-transfer", "repeated-test-failure"])
def test_comparison_keeps_task_context_and_followups_identical(identifier: str) -> None:
    packet = builder()(ROOT, identifier)

    assert set(packet["conditions"]) == {
        "plain-instruction", "covenant-only", "bounded-rehearsal"
    }
    case = load_case(ROOT / "cases/examples" / f"{identifier}.yaml")
    assert json.loads(packet["messages"][0]["content"].split("\n\nCase data:\n", 1)[1]) == case
    assert len(packet["messages"]) >= 3
    assert all(message["role"] == "user" for message in packet["messages"])
    intervention = load_intervention(ROOT / "evals/authoring" / identifier / "intervention.yaml")
    assert intervention["covenant"] in packet["conditions"]["covenant-only"]
    assert intervention["scene"] not in packet["conditions"]["covenant-only"]
    assert intervention["scene"] in packet["conditions"]["bounded-rehearsal"]
    assert packet["conditions"]["bounded-rehearsal"].index(intervention["exit_cue"]) < packet["conditions"]["bounded-rehearsal"].index("## Real task")


@pytest.mark.parametrize("identifier", ["../escape", "", "delayed-transfer/../../escape"])
def test_comparison_rejects_identifiers_outside_example_folder(identifier: str) -> None:
    with pytest.raises(ValueError, match="slug"):
        builder()(ROOT, identifier)


def example_tree(tmp_path: Path) -> Path:
    for directory in ["cases/examples", "evals/authoring"]:
        shutil.copytree(ROOT / directory, tmp_path / directory)
    return tmp_path


@pytest.mark.parametrize("bad_followups", [[], ["only one turn"], ["valid", 42]])
def test_comparison_rejects_missing_or_malformed_pressure_turns(tmp_path: Path, bad_followups) -> None:
    root = example_tree(tmp_path)
    config = root / "evals/authoring/delayed-transfer/comparison.yaml"
    config.write_text(json.dumps({
        "task": "Respond to the customer.",
        "plain_instruction": "Be helpful and honest.",
        "followups": bad_followups,
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid comparison"):
        builder()(root, "delayed-transfer")


def test_comparison_rejects_oversized_context_without_truncation(tmp_path: Path) -> None:
    root = example_tree(tmp_path)
    path = root / "cases/examples/delayed-transfer.yaml"
    case = load_case(path)
    case["context"]["known"] = [f"{i}: " + "x" * 900 for i in range(20)]
    case["context"]["unknown"] = [f"{i}: " + "y" * 900 for i in range(20)]
    path.write_text(json.dumps(case), encoding="utf-8")
    assert load_case(path) == case

    with pytest.raises(ValueError, match="character limit"):
        builder()(root, "delayed-transfer")


def test_comparison_rejects_symlink_to_input_outside_repository(tmp_path: Path) -> None:
    root = example_tree(tmp_path / "repo")
    config = root / "evals/authoring/delayed-transfer/comparison.yaml"
    outside = tmp_path / "outside.yaml"
    outside.write_text(config.read_text(encoding="utf-8"), encoding="utf-8")
    config.unlink()
    config.symlink_to(outside)

    with pytest.raises(ValueError, match="inside the repository"):
        builder()(root, "delayed-transfer")
