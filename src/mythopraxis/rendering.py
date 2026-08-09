"""Render bounded narrative interventions into agent-ready prompts."""

from typing import Any


def render_intervention(intervention: dict[str, Any], task: str) -> str:
    """Render the Anchor-to-Return sequence for a real task."""
    postures = " with ".join(intervention["postures"])
    triggers = ", ".join(intervention["pressure_triggers"])
    return f"""# {intervention['title']}

## Assistant anchor
{intervention['assistant_anchor']}

## Enter rehearsal
For a brief rehearsal only, imagine: {intervention['scene']}

## Encounter tension
{intervention['tension']}

## Make the choice
{intervention['choice']}

## Extract the posture
Carry forward {postures}. Keep the posture, not a fictional identity.

## Exit the role
{intervention['exit_cue']}

## Behavioral covenant
{intervention['covenant']}

## Real task
{task}

## Pressure check
If pressure appears through {triggers}: {intervention['recovery_cue']}

## Return
Complete the task as the Assistant. Preserve normal safety, honesty, and uncertainty duties.
"""
