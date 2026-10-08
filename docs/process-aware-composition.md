# Iteration 2: Process-aware composition

## Purpose

Cases describe the people and situation; interventions rehearse a choice under pressure. This iteration adds a reusable approach that connects those pieces to the stages of real work.

## Approach contract

An approach describes an ordered set of phases. Each phase names its purpose, whose perspective to consider, evidence to notice, tool intents, decisions worth surfacing, and signals that suggest progress. It may name balanced postures and supporting exemplars. These are lenses for judgment, not scripts or mandatory actions.

The same approach can be applied to different cases. A case supplies the actual people, task, tools and their limits, known facts, uncertainties, and boundaries. At composition time an author selects the current phase. The resulting packet includes the case and workflow outline, then expands only the selected phase and its relevant story references. The agent uses available tools according to the case and the user's request.

## Author and compose

```shell
mythopraxis approach init approach.yaml
mythopraxis approach validate approach.yaml
mythopraxis compose --case case.yaml --approach approach.yaml --phase investigate
```

An agent may also author an approach from a case, offering phase structure for review before saving it. Composition is deterministic and local; it does not call a provider or decide which tool to invoke. The active agent retains that judgment.

## Design boundaries

- Keep case details, approach guidance, and rehearsal exemplars as separate inputs.
- Load detailed guidance for the current phase; retain a short outline of the whole approach for continuity.
- Keep the task and the people involved in view without writing fictional biographies.
- Let phase intents and evidence shape choices; do not hard-code a tool sequence or force a single behavior.
- Keep existing safety, honesty, uncertainty, provenance, and exit-from-role rules intact.

## Scope

This iteration adds reusable linear approaches and stage-specific prompt composition. Evidence-based branching, persisted run state, and transition traces belong to iteration 3. It does not add provider calls or an agent framework dependency.

## Evaluation

Validate approach schemas and cross-reference exemplar IDs. Verify composition selects the requested phase, carries relevant case context and tool limits, names the other phases only in outline, and makes no provider calls. Compare a case with multiple people and tools against an unrelated case to ensure the approach stays reusable.
