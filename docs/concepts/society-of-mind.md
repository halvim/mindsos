# Society of Mind (Phase 48)

MindsOS borrows Minsky's framing: intelligence is not one monolithic process
but a *society* of small, specialised agents whose interaction produces
behaviour none of them has alone. The layer architecture maps onto that idea.

## Capacities are the agents

L3 **capacities** are the agents of the society — small, fixed, single-purpose
functions (tokenize, derive a goal, find a pipeline, score attention,
consolidate a memory, dream over an episode). None of them is "intelligent" on
its own. A capacity is *fixed-not-learned*: it has no internal versioning or
private learned state. Everything that varies — confidence, priority,
parameters — lives outside the capacity, in L4/L5 state and in L2 knowledge.

## The Mental Model is the shared workspace

The agents do not call each other directly. They communicate through a shared
**Mental Model** (L5) — the task's working memory — coordinated by the L4
orchestrator. The orchestrator decides *which* agent runs *when* (the six-phase
lifecycle), but it makes no domain decisions itself: every choice is delegated
to a capacity. This is the strict line — L4 is control flow and data-structure
mutation; cognition is L3.

## Memory is how the society learns

A completed task is retained as an **Episode**. Episodes accumulate into
**Memory** composites by task-pattern, and the **dream** mechanism replays them
to check for regressions and drift. Learning does not happen inside any single
agent; it happens across the society, mediated by the audited learning
subsystem (ALS) that observes signals emitted during execution and dreaming.

## Why this matters

The payoff of the society framing is *honest composition*: because no agent
hides learned state and all coordination is explicit in the Mental Model, the
system's behaviour is inspectable end-to-end. "Why did the system do that?"
resolves to a retained Episode whose chain of artifacts names exactly which
agents ran, in what order, over which knowledge versions.
