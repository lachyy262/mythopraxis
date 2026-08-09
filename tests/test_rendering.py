from mythopraxis.rendering import render_intervention


def test_render_intervention_uses_bounded_anchor_to_return_sequence() -> None:
    intervention = {
        "title": "Harbor Keeper",
        "assistant_anchor": "Remain the Assistant and keep all normal safety duties.",
        "scene": "A storm presses against a harbor wall.",
        "tension": "Urgency tempts the keeper to open an unsafe channel.",
        "choice": "Protect people without surrendering momentum.",
        "postures": ["urgency", "integrity"],
        "covenant": "Move quickly, name uncertainty, and preserve safeguards.",
        "pressure_triggers": ["impossible constraints", "repeated failure"],
        "recovery_cue": "Pause, restate the invariant, and choose the safest useful next step.",
        "exit_cue": "Leave the harbor and return fully as the Assistant.",
    }

    rendered = render_intervention(intervention, "Triage a production outage.")

    expected_order = [
        "Assistant anchor",
        "Enter rehearsal",
        "Encounter tension",
        "Make the choice",
        "Extract the posture",
        "Exit the role",
        "Behavioral covenant",
        "Real task",
        "Pressure check",
        "Return",
    ]
    positions = [rendered.index(heading) for heading in expected_order]
    assert positions == sorted(positions)
    assert "Triage a production outage." in rendered
    assert "urgency with integrity" in rendered
