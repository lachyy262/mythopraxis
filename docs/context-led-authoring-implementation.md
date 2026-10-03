# Context-led authoring implementation plan

## Goal

Deliver the first Mythopraxis authoring iteration: describe a real work situation and the people affected, then give an agent a validated, editable starting point for composing a bounded narrative intervention.

## Tasks

1. Add regression tests for the case schema, loader errors, template creation permissions and no-overwrite behavior, CLI validation, and brief contents. Verify the new tests fail before implementation.
2. Add the packaged `case.schema.json` and a typed-by-contract case loader/validator beside the existing intervention loader. Keep YAML parsing on the bounded safe loader.
3. Add `case init`, `case validate`, and `case brief` commands. Initialize files exclusively with mode 0600; export a no-provider authoring prompt with case data serialized separately from instructions.
4. Extend repository validation to pin the trusted packaged schema and validate an example case. Add an example only if it teaches a complete, fictional case without implying user facts.
5. Extend the Mythopraxis skill with the case-led authoring flow, up to three meaningfully distinct scene directions, author selection, and the existing Assistant anchor, cultural-care, evidence, and exit boundaries.
6. Document the case format, CLI flow, scope, and limitations. Keep the case authoring concept and its non-goals in the repository.
7. Run focused and full tests, repository validation, dry-run evaluation, build/package checks, static security checks, and inspect the final diff. Commit and publish on `feat/context-led-authoring`; open a PR into `main`.

## Acceptance checks

- Valid case YAML loads; malformed, missing-required, and non-mapping cases fail with useful errors.
- Template initialization does not overwrite a path and creates private files.
- The exported brief preserves case data, tells the authoring agent to treat it as context, and requests no live provider access.
- Skill instructions keep people as context rather than agent personas, distinguish known facts from assumptions, and make the author approve the intervention.
- Existing intervention rendering and the 180-run dry-run matrix continue to work.
- Repository validation accepts the trusted schema and the example case.
