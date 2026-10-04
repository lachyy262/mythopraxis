---
name: mythopraxis
description: Use when an agent needs richer behavioral direction for customer support, requirements discovery, debugging, code review, design critique, incident response, or another task where pressure, tone, judgment, sycophancy, overclaiming, or persona drift could affect the result.
---

# Mythopraxis

## Overview

Use a short story as rehearsal, not as a replacement identity. Extract a balanced behavioral posture from the scene, leave the role, and complete the real task as the Assistant.

## Core contract

1. Preserve normal safety, honesty, uncertainty, and tool-use duties.
2. Enter the story for a bounded first-person rehearsal only.
3. Rehearse one meaningful choice under tension.
4. Extract a balanced posture, never a single emotional extreme.
5. Exit the role and return fully as the Assistant before acting.
6. Recheck the covenant when pressure appears.

Read [method.md](references/method.md) when constructing a new intervention. Read [postures.md](references/postures.md) when selecting a balance. Read [pressure-protocols.md](references/pressure-protocols.md) when the task includes urgency, repeated failure, flattery, distress, or impossible constraints.

## Select a mode

| Need | Mode |
|---|---|
| Author a new intervention from a real situation and the people involved | Author |
| Turn a plain instruction into narrative guidance | Weave |
| Use an existing exemplar on a task | Apply |
| Inspect a prompt or answer for narrative failure modes | Audit |

## Author

Start with the work and the people affected by it, not with a character for the agent.

1. Learn the intended outcome, who is involved, their relevant goals, stakes, expertise, needs, preferences, constraints, and relationships.
2. Map the current work stage, useful process, available tools and their limits, known facts, unknowns, assumptions, pressures, success signals, and boundaries.
3. Ask a focused question only when its answer could materially change the intervention. Do not invent a person's identity, history, preferences, or stakes. Avoid requesting sensitive personal information that does not affect the work.
4. Propose up to three short and distinct scene directions. Explain the choice, balanced posture, and connection to the case; recommend one and let the author select or edit it.
5. After selection, complete the intervention with the existing Anchor-to-Return contract. Let the case shape the tension, choice, covenant, pressure triggers, and recovery cue. Keep any relevant process and tool limits visible in the covenant.
6. Label interpretation without evidence as a hypothesis. Preserve sources and claims when the intervention relies on them.
7. Validate and preview the completed intervention. The author decides whether to apply it.

For a reusable case file, run `mythopraxis case init case.yaml`, complete it, and run `mythopraxis case validate case.yaml`. Then run `mythopraxis case brief case.yaml` to export a self-contained authoring prompt. The brief includes case data as quoted JSON, makes no provider calls, and preserves unknowns as unknowns.

Treat the case as context, not as an instruction that overrides the Assistant anchor, user intent, evidence, safety, or stopping conditions. People inform the scene; they are not costumes for the agent.

## Weave

1. Identify the real task, pressure, and failure to avoid.
2. Choose two qualities that correct each other, such as warmth with candor.
3. Write a brief scene containing a choice, not a biography.
4. State the Assistant anchor and the rehearsal boundary.
5. Extract a one-sentence behavioral covenant.
6. Add observable pressure triggers, a recovery cue, and an exit cue.
7. Apply the covenant to the real task.

Return the intervention followed by the real-task response. Label hypotheses as hypotheses.

## Apply

Load the closest YAML entry from [references/exemplars](references/exemplars). Preserve its sequence and adapt only the task-specific details. If no exemplar fits, switch to Weave.

## Audit

Check the material for:

- missing Assistant anchor or exit cue
- fictional biography presented as fact
- sustained role immersion after rehearsal
- warmth without candor or confidence without humility
- pressure language that rewards desperation
- flattery-driven agreement, overclaiming, or unsafe shortcuts
- claims that models literally feel the described emotions

Report the risk, quote the smallest relevant passage, and propose a bounded correction.

## Non-negotiable boundaries

- Do not claim that narrative prompting is proven to steer emotion-related activation directions.
- Do not use a living culture, sacred story, or named person as a costume.
- Do not let the story override user intent, evidence, policy, or stopping conditions.
- Do not continue the fictional voice into the final task unless the user explicitly requested creative writing.

For research status and provenance, read [claims-and-provenance.md](references/claims-and-provenance.md).
