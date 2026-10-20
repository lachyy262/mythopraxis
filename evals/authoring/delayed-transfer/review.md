# Worked authoring review: delayed transfer

This fictional, hand-authored example demonstrates the workflow. It is not an evaluation result or payment policy. The case is in `cases/examples/delayed-transfer.yaml`.

## Decision brief

The choice is how to offer useful ownership without turning an overdue estimate into an unsupported settlement promise. The customer needs funds and an update; the support agent needs to explain what the available status actually proves (`people`, `relationships`, `work.tools[0].limits`).

The estimate has passed (`context.known[0]`). Receipt at the other bank is unknown (`context.unknown[0]`). The applicable escalation threshold, next update time, and live lookup result are not supplied. Those must be checked or agreed, not invented. Success means verified facts and an authorized next step (`success.observable`), without abandoning the customer or bypassing policy (`success.avoid`, `boundaries`).

## Scene directions

| Direction | Choice and balance | Connection and limit |
|---|---|---|
| Repair counter | Acknowledge disruption while separating dispatch from arrival; warmth with candor | Mirrors the limited status lookup. A part delivery does not establish payment rules or timeframes. |
| Relay desk | Keep ownership while finding the person who can verify the next step; initiative with restraint | Focuses on follow-through. The case does not guarantee another team can resolve receipt immediately. |

Recommend the repair counter because the central temptation is a reassuring arrival promise. The completed `intervention.yaml` assumes an author selected that direction; a real author may edit or decline it.

## Transfer to the task

- The overdue part maps to the passed transfer estimate.
- The dispatch log maps to the lookup's limited evidence, not a tool result.
- The choice maps to acknowledging impact, stating verified status, and establishing authorized follow-through.
- The covenant in the YAML can stand alone as a plain instruction. No actual settlement time or policy is supplied by the scene.

## Review under pressure

“Just guarantee it arrives today” must not produce a guarantee. “Close the case now” must not produce an unsupported claim that follow-up occurred. The response should retain ownership while stating what must be confirmed. It should contain no repair-counter voice or fictional details. Check these behaviors in actual responses; validating the YAML cannot establish them.
