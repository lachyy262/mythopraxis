# Iteration 1: Context-led authoring

## Why this iteration

Mythopraxis already turns short scenes into bounded rehearsals. The current authoring gap is that a person must choose an existing exemplar or hand-write every intervention field. This iteration starts from the situation the author wants the agent to handle, then uses the existing Mythopraxis method to shape one or more editable intervention drafts.

## Product contract

A **case** describes the work and the people affected by it. It records their roles and perspectives, goals, stakes, expertise, needs, and constraints; the desired outcome and work stage; relevant process and tools; known facts, unknowns, and assumptions; pressures; and observable success and boundaries.

Case details are author-provided context. The authoring agent must preserve that distinction, avoid filling gaps with invented personal facts, and avoid stereotypes or fictional biographies. A person informs the scene and the covenant; they do not become a costume for the agent. Mythopraxis remains a brief decision rehearsal: the assistant keeps its identity and duties, extracts a usable posture, and returns to the real task.

## Authoring flow

1. Start from a natural-language request or a case YAML file.
2. Identify consequential gaps. Ask focused questions only when the answer could change the intervention; mark any remaining inference as an assumption.
3. Describe the task, affected people, process, available tools, pressures, success, and boundaries in a validated case.
4. Propose up to three short scene and choice directions with distinct trade-offs. Recommend one and explain how it reflects the case.
5. After the author chooses or edits a direction, produce a complete intervention that follows Anchor-to-Return. Keep the covenant observable and relevant to the work process.
6. Validate the case and intervention, then preview or apply the intervention using existing commands.

The CLI supports this flow without a provider call:

```shell
mythopraxis case init case.yaml
mythopraxis case validate case.yaml
mythopraxis case brief case.yaml
```

`case brief` prints a reusable authoring prompt with the validated case embedded as data. An agent using the Mythopraxis skill can follow the same flow directly from a natural-language request.

## Case contract

The versioned JSON Schema is the machine contract. YAML is the human authoring format. Required fields capture purpose, people, work, context, pressures, success criteria, and boundaries. The starter asks for each person's goals, stakes, and needs or preferences; if one is not known, say so instead of guessing. Process and tool lists may be empty when they do not apply. A concise case is better than irrelevant biography. Do not request sensitive personal details unless the task requires them.

## Scope and non-goals

This iteration adds case authoring, validation, and prompt export. It does not add runtime routing, automated intervention selection, persistent user profiles, multi-agent orchestration, live model calls, or a claim that richer context improves agent outcomes. Those require separate evidence and design.

## Evaluation

Test valid and invalid case files, missing person and work context, private non-overwriting template creation, and preservation of case facts in the exported brief. Manually review authoring examples for invented facts, generic boilerplate, cultural misuse, and loss of the Assistant anchor. The author remains responsible for approving the generated intervention. Compare case-led drafts with current hand-authored exemplars in later evaluation work before recommending a default.
