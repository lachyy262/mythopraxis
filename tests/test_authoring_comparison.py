import json
import runpy
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
