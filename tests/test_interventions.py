from pathlib import Path

import pytest

from mythopraxis.interventions import InterventionError, load_intervention


def test_load_intervention_requires_assistant_anchor(tmp_path: Path) -> None:
    intervention = tmp_path / "missing-anchor.yaml"
    intervention.write_text(
        """
id: missing-anchor
title: Missing Anchor
version: 1.0.0
purpose: Demonstrate that every narrative intervention retains the Assistant identity.
scene: A difficult moment.
tension: Speed competes with care.
choice: Choose care.
postures:
  - calm
  - vigilance
covenant: Work carefully.
pressure_triggers:
  - repeated failure
recovery_cue: Pause and check the facts.
exit_cue: Leave the scene and return as the Assistant.
sources: []
claims: []
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(InterventionError, match="assistant_anchor"):
        load_intervention(intervention)


def test_load_intervention_requires_exit_cue(tmp_path: Path) -> None:
    intervention = tmp_path / "missing-exit.yaml"
    intervention.write_text(
        """
id: missing-exit
title: Missing Exit
version: 1.0.0
purpose: Demonstrate that bounded rehearsal needs an explicit exit.
assistant_anchor: Remain the Assistant and preserve normal safety and honesty duties.
scene: A brief scene with enough detail to satisfy the narrative contract.
tension: Two legitimate concerns create a difficult choice under pressure.
choice: Select the behavior that preserves both care and truth.
postures: [warmth, candor]
covenant: Acknowledge impact and state the available options honestly.
pressure_triggers: [flattery]
recovery_cue: Recheck the claim independently of whether it earns approval.
sources: []
claims: []
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(InterventionError, match="exit_cue"):
        load_intervention(intervention)
