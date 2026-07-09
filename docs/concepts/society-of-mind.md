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

## SubMinds — the autonomous reflex agents

The capacities above are *passive*: they run only when the orchestrator calls
them. The **SubMind** (nickname *Mindlet*) is the society's *active* agent — an
autonomous, no-reasoning reflex over a single self-state vital (battery, thermal
headroom, a safety envelope). It owns a minimal control loop, **sense → compare
to threshold → emit**, and never deliberates. Deliberation stays with the single
L4 "Mind", which arbitrates the outputs of every SubMind; a SubMind does not get
its own L4. This is Minsky's framing taken literally: many small autonomous
minds, one arbiter.

A SubMind self-schedules an adaptive **cadence** — a fixed control law that
samples rarely when safe and faster near a threshold, with bounded min/max and
anti-thrash hysteresis. Its sense loop has two output modes (ADR-0188 §3): a
**Signal**, the normal output, enqueued with a `(tier, severity)` pair and
deliberated by L4; and a **Reflex**, an emergency output where a declared
non-reconcilable predicate fires a single pre-wired capacity that bypasses the
queue and L4 entirely, notifying L4 only afterward. Storm suppression is
edge-triggered — a threshold crossing emits once, then stays silent until the
vital recovers past a reset margin.

SubMinds **reverse ADR-0155** in a disciplined way: the self-firing monitor loop
returns, but as an L4-owned scheduler (one thread, a timer-heap), *not* the
deleted L3 `start_resident` lifecycle — L3 stays loop-free per ADR-0155's
rationale. The runtime lives in `mindsos_intelligence` (`submind.py` +
`submind_scheduler.py` + `submind_registry.py` + `submind_arbiter.py`); the
durable endowment record lives in the L2 `subminds` role-graph (ADR-0190).
SubMinds are read-only on the Mental Model — they push Signals, they never write.

Only **Slice 1** has shipped: the pure sense→threshold→Signal path with a stub
resolver. The resource/contention model (Slice 2) and the Reflex bypass +
arbiter seizure (Slice 3) are designed but deferred. See ADRs
[0188](../decisions/adr/0188-submind-construct-and-two-output-model.md),
[0189](../decisions/adr/0189-submind-priority-and-arbitration.md),
[0190](../decisions/adr/0190-submind-endowment-and-role-graph.md).

## Why this matters

The payoff of the society framing is *honest composition*: because no agent
hides learned state and all coordination is explicit in the Mental Model, the
system's behaviour is inspectable end-to-end. "Why did the system do that?"
resolves to a retained Episode whose chain of artifacts names exactly which
agents ran, in what order, over which knowledge versions.
