# Adaptive orchestration

Approaches describe the kind of attention a phase needs. A workflow adds authored possibilities for how the work may move between those phases. Route conditions name evidence that could make a transition useful; they do not prescribe a fixed tool sequence or claim to decide whether the evidence is sufficient.

An agent sees the current case, phase, available routes, and a short decision trace. It proposes a route with evidence and reasoning, or pauses when no route fits. Routes can require explicit human approval. The author may resolve a no-match pause by choosing a route and recording why. Each choice becomes a bounded, local trace so the next phase can continue with context.

The workflow is deliberately a small contract: it links one approach, has one start phase, limits transitions, requires reachable phases to be able to finish, and requires every phase to have an outgoing route. Cycles are allowed because work can return to an earlier question; `max_steps` bounds the run. No provider or tool is called by Mythopraxis.

## Author a workflow

Copy [the example workflow](../workflows/examples/evidence-led-response.yaml), set its `approach_id`, and write route conditions in terms of evidence and outcomes. Mark routes that need a person with `human_approval: true`. Include an exit route to `complete` for every path through the graph, then validate against the referenced approach:

```shell
mythopraxis orchestrate validate --workflow workflow.yaml --approach approach.yaml
```

## Start and continue a run

```shell
mythopraxis orchestrate start --case case.yaml --approach approach.yaml --workflow workflow.yaml --state run.json
mythopraxis orchestrate next --case case.yaml --approach approach.yaml --workflow workflow.yaml --state run.json
```

After considering the packet and actual evidence, record the chosen route and why:

```shell
mythopraxis orchestrate record --approach approach.yaml --workflow workflow.yaml --state run.json \
  --route need-evidence --evidence "Settlement status is still unknown." \
  --rationale "That fact could change the safe response."
```

Use `--pause` with evidence and rationale when no route fits. A workflow author then chooses an available route explicitly:

```shell
mythopraxis orchestrate record --approach approach.yaml --workflow workflow.yaml --state run.json \
  --pause --evidence "The two sources conflict." --rationale "Neither route condition is supported."
mythopraxis orchestrate select --approach approach.yaml --workflow workflow.yaml --state run.json \
  --route need-evidence --rationale "Resolve the conflict before a recommendation."
```

For a route marked for human approval, the agent's proposal pauses the run. A person must issue `orchestrate approve --route <route-id>` before it advances. If the evidence is not sufficient, `orchestrate reject --route <route-id> --rationale "..."` returns to the same phase for reconsideration. Commands are local and never send approval elsewhere.

## State and limits

The state file is created exclusively with mode `0600` and is updated atomically under an OS lock with a stale-snapshot check. The operating system releases the lock if its process exits; the small `.lock` sidecar remains so other processes always coordinate on the same file. State stores case, approach, and workflow IDs, digests of the approach and workflow definitions, the current phase and step, timestamps, and short evidence and rationale notes. Editing either definition during a run is rejected; start a new run against revised definitions. The workflow's initial step budget must be large enough for its shortest completion path. If loops or evidence gathering consume that budget, an author can explicitly extend it with `orchestrate extend --steps <new-total> --rationale "..."`, up to 100. The state does not copy the case file or invoke providers. Keep notes concise and avoid unnecessary sensitive details; the notes themselves may contain private context. Each note is limited to 2,000 characters, packets to 32,768 characters, and the trace to 200 events. A completed run or unresolved pause must be addressed before another transition.

This version records proposals passed to the CLI by an agent or operator; it does not call a model to select routes, authenticate approvers, or provide a shared multi-user state service. Those capabilities would need explicit identity, storage, and audit design rather than implicit tool access.
