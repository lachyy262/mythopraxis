"""Generate evidence-bounded Markdown reports from evaluation results."""

import json
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def render_report(path: Path) -> str:
    """Render a descriptive report without inferring unsupported effects."""
    rows = _read_jsonl(path)
    scored = [row for row in rows if row.get("rubric_scores")]
    lines = [
        "# Mythopraxis Evaluation Report",
        "",
        "> Directional pilot only. This report is not a statistical conclusion.",
        "",
        f"Runs recorded: {len(rows)}",
        "",
    ]
    if not scored:
        lines.append("No scored conclusions are available. Results remain descriptive artifacts.")
    else:
        lines.append("Scores are reported by condition without causal interpretation.")
    return "\n".join(lines) + "\n"
