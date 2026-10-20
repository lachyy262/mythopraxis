from pathlib import Path

import pytest

from mythopraxis.cases import authoring_brief, load_case
from mythopraxis.interventions import load_intervention
from mythopraxis.rendering import render_intervention


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("identifier", ["delayed-transfer", "repeated-test-failure"])
def test_worked_example_can_be_authored_validated_and_rendered(identifier: str) -> None:
    case = load_case(ROOT / "cases/examples" / f"{identifier}.yaml")
    intervention = load_intervention(
        ROOT / "evals/authoring" / identifier / "intervention.yaml"
    )

    brief = authoring_brief(case)
    rendered = render_intervention(intervention, case["work"]["outcome"])

    assert case["purpose"] in brief
    assert case["work"]["outcome"] in rendered
    assert intervention["covenant"] in rendered
    assert rendered.index(intervention["exit_cue"]) < rendered.index("## Real task")
