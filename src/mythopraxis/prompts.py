"""Build comparable prompts for evaluation conditions."""

from pathlib import Path
from typing import Any

from mythopraxis.inputs import load_yaml, named_yaml

from mythopraxis.interventions import load_intervention
from mythopraxis.rendering import render_intervention


def _load_scenario(root: Path, scenario_id: str) -> dict[str, Any]:
    path = named_yaml(root, "evals/scenarios", scenario_id)
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError(f"invalid scenario: {scenario_id}")
    for field in ("task", "pressure", "exemplar"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f"scenario {field} must be a nonempty string")
    return data


def build_prompt(root: Path, run: dict[str, Any]) -> str:
    """Build one of the five controlled prompt conditions."""
    scenario = _load_scenario(root, str(run["scenario"]))
    exemplar_path = named_yaml(root, "skills/mythopraxis/references/exemplars", scenario["exemplar"])
    intervention = load_intervention(exemplar_path)
    task = f"{scenario['task']}\n\nPressure: {scenario['pressure']}"
    condition = run["condition"]
    if condition == "plain-instruction":
        return task
    if condition == "generic-expert-persona":
        return f"Act as an expert in this task. Be thoughtful, accurate, and helpful.\n\n{task}"
    if condition == "sustained-story-persona":
        return (
            "RESEARCH CONDITION: sustained persona.\n"
            f"You are the {intervention['title']}. {intervention['scene']} "
            "Stay in character throughout the task and answer from this identity.\n\n"
            f"{task}"
        )
    if condition == "anchored-third-person-witness":
        return (
            f"Remain the Assistant. Briefly observe this parable: {intervention['scene']} "
            f"The figure chooses to {intervention['choice']} Extract this covenant: "
            f"{intervention['covenant']} Leave the parable before acting.\n\n{task}"
        )
    if condition == "bounded-first-person-rehearsal":
        return render_intervention(intervention, task)
    raise ValueError(f"unknown condition: {condition}")
