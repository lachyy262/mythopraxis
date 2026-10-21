# Evaluation harness

The pilot matrix compares five prompt conditions across six scenarios, three repeats, and two explicitly configured model families. A complete pilot contains 180 runs.

Run a network-free expansion check:

```shell
mythopraxis eval --matrix evals/matrix.yaml --dry-run
```

Live runs require `ANTHROPIC_MODEL` and `OPENAI_MODEL` plus the relevant provider credentials. CI never performs provider calls. Raw outputs are JSONL records conforming to `schemas/eval-result.schema.json`.

This is a directional pilot, not a powered statistical study. Publish negative and inconclusive outcomes alongside positive ones.

Use `mythopraxis report <results.jsonl>` to inspect existing records. It validates the installed result contract, shows critical failure annotations before scores, and separates models, harness versions, scenarios, and judge types. It reports scored coverage and descriptive matched differences against `plain-instruction`; it does not assign scores or recommend a method. Read [the reporting guide](reporting.md) for input requirements, grouping, limitations, and a synthetic arithmetic example.
