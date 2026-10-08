# Process-aware composition implementation plan

## Goal

Let authors define reusable work approaches and compose a case with the current phase into a focused, portable agent prompt.

## Tasks

1. Add tests first for approach validation, bounded initialization, selected-phase composition, case/tool context, and CLI error behavior.
2. Add a packaged approach schema and loader. Require at least two ordered phases; keep tool and evidence descriptions semantic rather than prescriptive.
3. Add private approach init and offline approach validate commands.
4. Add compose --case --approach --phase to validate both inputs and export a bounded packet with the overall outline and selected phase detail. Do not make provider calls or invoke tools.
5. Add one reusable example approach and repository checks for its schema and exemplar references.
6. Extend the Mythopraxis skill and README with approach authoring and phase composition. Persist the design boundaries and scope here.
7. Run focused tests, full tests, repository validation, a composed prompt check, the existing dry-run matrix, security checks, and diff checks. Commit to feat/process-aware-composition; publish as a branch stacked on context-led authoring.

## Acceptance checks

- The same approach can be composed with different valid cases.
- Invalid phase IDs and malformed or oversized input fail before a prompt is emitted.
- Only current-phase detail is expanded; the complete phase sequence remains visible as an outline.
- Case tools are shown with their stated limits; phase tool intents remain guidance.
- Existing case, intervention, and evaluation behavior remains green.
