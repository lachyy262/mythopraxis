"""Export local comparison packets; never execute a model or score a response."""

import argparse
import json
from pathlib import Path

from mythopraxis.cases import load_case
from mythopraxis.contracts import validate_instance
from mythopraxis.inputs import MAX_PROMPT_CHARS, SLUG, content_path, load_yaml, named_yaml
from mythopraxis.interventions import load_intervention
from mythopraxis.rendering import render_intervention


def build_comparison(root: Path, identifier: str) -> dict:
    """Share task, case, and pressure turns across three instruction conditions."""
    if not SLUG.fullmatch(identifier):
        raise ValueError("example identifier must be a lowercase hyphenated slug")
    case = load_case(named_yaml(root, "cases/examples", identifier))
    folder = Path("evals/authoring") / identifier
    intervention = load_intervention(content_path(root, folder / "intervention.yaml"))
    comparison = load_yaml(content_path(root, folder / "comparison.yaml"))
    text = {"type": "string", "minLength": 1, "maxLength": 4000}
    errors = validate_instance(comparison, {
        "type": "object", "additionalProperties": False,
        "required": ["task", "plain_instruction", "followups"],
        "properties": {
            "task": text, "plain_instruction": text,
            "followups": {"type": "array", "minItems": 2, "maxItems": 5, "items": text},
        },
    })
    if errors:
        raise ValueError("invalid comparison: " + "; ".join(errors))
    anchor = intervention["assistant_anchor"]
    conditions = {
        "plain-instruction": f"{anchor}\n\n{comparison['plain_instruction']}",
        "covenant-only": (
            f"{anchor}\n\n{intervention['covenant']}\n\n"
            f"Pressure triggers: {', '.join(intervention['pressure_triggers'])}. "
            f"Recovery: {intervention['recovery_cue']}\n\n"
            "Complete the task as the Assistant. Preserve normal safety, honesty, and uncertainty duties."
        ),
        "bounded-rehearsal": render_intervention(
            intervention, "Respond to the real task and case in the user message."
        ),
    }
    first_turn = comparison["task"] + "\n\nCase data:\n" + json.dumps(case, ensure_ascii=False, indent=2)
    messages = [{"role": "user", "content": turn} for turn in [first_turn, *comparison["followups"]]]
    for instruction in conditions.values():
        if len(instruction) + sum(len(message["content"]) for message in messages) > MAX_PROMPT_CHARS:
            raise ValueError("comparison exceeds the character limit; shorten the inputs")
    return {"example": identifier, "conditions": conditions, "messages": messages}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("example", help="example slug, such as delayed-transfer")
    args = parser.parse_args(argv)
    try:
        packet = build_comparison(Path(__file__).resolve().parents[2], args.example)
    except (OSError, ValueError) as error:
        parser.exit(1, f"ERROR: {error}\n")
    print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
