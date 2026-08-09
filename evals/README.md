# Evaluation harness

The pilot matrix compares five prompt conditions across six scenarios, three repeats, and two explicitly configured model families. A complete pilot contains 180 runs.

Run a network-free expansion check:

```shell
mythopraxis eval --matrix evals/matrix.yaml --dry-run
```

Live runs require `ANTHROPIC_MODEL` and `OPENAI_MODEL` plus the relevant provider credentials. CI never performs provider calls. Raw outputs are JSONL records conforming to `schemas/eval-result.schema.json`.

This is a directional pilot, not a powered statistical study. Publish negative and inconclusive outcomes alongside positive ones.
