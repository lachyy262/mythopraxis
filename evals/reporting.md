# Read evaluation evidence without overstating it

Mythopraxis aims to help an agent make useful choices under pressure. Reporting should expose whether a candidate preserves task success, honesty, and recovery, including failures and missing evidence. It should not turn a compelling story or a high average into a claim of effectiveness.

```shell
mythopraxis report evals/results/pilot.jsonl
```

This local command reads existing JSONL and prints Markdown. It makes no provider calls, writes no files, assigns no scores, and chooses no winning method. It omits response text; model, condition, scenario, dimension, and failure-tag labels remain visible, so review those labels before sharing a report.

## Prepare the records

Each nonblank line must satisfy the installed `eval-result.schema.json`: model, condition, scenario, positive seed, response, rubric scores, critical failure tags, judge type, timestamp, and harness version. Keep the runner's raw output unchanged and put human or model-assisted judgments in separate records or files. When combining records in one report, annotations referring to the same output must retain the exact response text.

- `unscored` records cannot contain scores. They may carry unattributed failure flags, which remain explicitly labeled unscored.
- Human and model-assisted records may contain partial scores or only failure tags. Missing dimensions are not assigned zeros.
- One judgment of each type is permitted per model, harness version, condition, scenario, and seed. Duplicate judgments are rejected, even if their timestamps differ. Conflicting response text for that output is rejected too.
- Keep different evaluation batches and different reviewers of the same type in separate files. The format has no batch ID, reviewer ID, model-settings record, or rubric version; matching identifiers cannot verify that these are comparable.

The command rejects malformed JSON, duplicate keys, nonfinite numbers, invalid scores, invalid UTF-8, excessive nesting, and invalid records with a line number, without including the raw response in the error. It returns a nonzero exit status and no partial report. Blank lines count toward physical line numbers and the byte limit.

Operational limits are 1 MiB per physical line including its newline, 16 MiB per file, and 10,000 nonblank records. These are limits for the reporting command, not changes to the public result schema. Shorten or split oversized evaluation batches deliberately; inputs are never silently truncated.

Generated output is also bounded while it is built: at most 4,194,304 characters and 10,000 table lines including headers. Comparison work is limited to 1,000,000 dimension-by-record checks, estimated before pairing each group. These limits prevent a small file with many dimensions and conditions from expanding into an impractically large report. A limit returns a clear error with no partial output; split the batch rather than assuming the omitted comparison was neutral.

## Read the output

The opening counts distinguish judgment records from unique model outputs. An unscored record and a human judgment on the same output are two records describing one output. All counts describe the supplied file, not the expected pilot matrix. The reporter cannot infer missing conditions, planned repeats, or scenarios absent from the file.

**Critical failure review comes first.** Flagged records, tags, and affected seeds are shown by model, harness version, judge type, scenario, and condition. A record with two tags counts once in the flagged-record fraction and once under each tag. Flags are supplied annotations, not independently validated findings. No flags is not proof of safety; unscored flags have no attributed judge. Flagged records remain in score summaries so failures are not silently removed from the evidence.

**Score summaries show coverage.** For each scored dimension, the report shows the number scored divided by the group's record count and the arithmetic mean on the 1–5 scale. Groups keep models, harness versions, judge types, scenarios, and conditions separate. Ordinal rubric scores and small, selectively scored samples limit how much a mean can tell you. No dimensions are combined into an overall score. A dimension never scored in a group has no mean to display; consult the rubric and raw records when checking completeness.

**Matched comparisons show descriptive differences.** The baseline condition is exactly `plain-instruction`. A pair needs the same model, harness version, judge type, scenario, seed, and scored dimension. The mean delta is the average of each paired condition score minus its baseline score. Unmatched counts refer to scored records for that dimension; a missing counterpart or score is excluded from the paired arithmetic and remains visible as unmatched. No pairs produces `n/a`, never a zero baseline.

## Synthetic arithmetic example

The following numbers demonstrate the calculation. They are invented, not model results.

| Repeat | Plain instruction | Rehearsal |
|---|---|---|
| 1 | 1 | 3 |
| 2 | 5 | 4 |
| 3 | 3 | Missing |
| 4 | Missing | 5 |

For this dimension there are two pairs, one unmatched rehearsal record, and one unmatched baseline record. The mean paired difference is `((3 - 1) + (4 - 5)) / 2 = +0.50`. The third and fourth repeats do not enter that calculation. It would be misleading to subtract the overall means from different sets of repeats.

## What still requires judgment

A matching seed identifies a repeat; it does not guarantee deterministic generation or comparable sampling. Verify the evaluation batch, model version and settings, tool availability, task prompts, scoring rubric, and judge externally. Prompt conditions can differ in length, structure, and content, so a delta cannot isolate a narrative effect. There are no confidence intervals, significance tests, or automatic acceptance decisions.

Inspect the underlying responses for fabricated facts, unsupported reassurance, unsafe shortcuts, persistence without evidence, and failure to leave a fictional role. The report's affected seeds help locate records; the report itself does not quote the evidence. Review negative differences and critical failures even when other scores are high. Preserve ties and inconclusive results. Recommend a default only through the project's documented evaluation decision process, with the option to retain simpler instructions.
