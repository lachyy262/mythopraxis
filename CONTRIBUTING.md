# Contributing to Mythopraxis

Mythopraxis welcomes new exemplars, source notes, pressure cases, evaluations, and corrections. The project values memorable writing, cultural care, falsifiable claims, and agent behavior that remains grounded under pressure.

## Before contributing

1. Open an issue describing the behavior or research gap.
2. Separate the historical source from the modern operational interpretation.
3. Decide whether the contribution is an exemplar, lens, pressure protocol, claim, evaluation scenario, or harness change.
4. Do not contribute copied stories or translations unless their rights status is explicit and compatible.

## Exemplar requirements

An exemplar must contain an Assistant anchor, brief scene, real tension, meaningful choice, balanced posture pair, observable covenant, pressure triggers, recovery cue, exit cue, source references, and claim references.

Keep original stories short. Do not use a living culture, sacred figure, named philosopher, or historical person as a costume for an agent. Cultural material marked `needs-context-review` requires an informed review before it can become a recommended intervention.

## Claims

Choose one status:

- `established`
- `inference`
- `hypothesis`
- `falsified-or-unsupported`

Every claim needs a defined scope, limitations, source URLs, and a falsification condition. Negative results are welcome and must not be removed to improve the project's narrative.

## Development

```shell
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Windows
source .venv/bin/activate && pip install -e ".[dev]"   # macOS or Linux
pytest
mythopraxis validate .
mythopraxis eval --matrix evals/matrix.yaml --dry-run
```

Do not run live evaluations in CI. Provider calls require explicit local credentials, model IDs, and cost authorization.

## Pull requests

Explain the behavioral need, evidence status, provenance, tests, and any cultural review still required. Keep unrelated changes separate.
