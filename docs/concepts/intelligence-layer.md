# Intelligence Layer (L4 substrate)

Layer 4 is the runtime that drives a session. It is **substrate and control
flow only**: every decision or computation is an L3 capacity that L4 invokes;
L4 owns lifecycle, threading, queue mechanics, lock arbitration, and state
plumbing (Chat A R1 strict line). The first L4 code ships at Phase 46 as the
`mindsos_intelligence` package — the substrate primitives, ahead of the Phase
47 orchestrator that exercises them.

## IntelligenceLayer lifecycle

One `IntelligenceLayer` per session. `start(...)` wires the substrate;
`enqueue(task, *, tier=...)` submits a unit of work to the Executor and returns
a `Future`; `stop(mode="abort")` cooperatively cancels in-flight work and tears
the substrate down. `mode="pause"` is deferred post-v1 (Push 5) and raises
`NotImplementedError`.

## Priority-tier Executor

A custom Executor (ADR-0163) over a priority heap keyed
`(tier, -attention_score, submit_time)`. The four tiers — CRITICAL, FOREGROUND,
BACKGROUND, DREAM — come from the L3 `TierEnum` (ADR-0169), imported downward.
Within a tier, ordering is by descending `attention_score` (cold-start
constants at v1; the L3 `scoring.attention_score` capacity lands Phase 47). The
single mutation primitive is `write_priority(task_id, score=None, tier=None)`;
`score=None` with a `tier` is the "top of new tier" elevate default. Ordering is
queue-level; running-task preemption is cooperative — a higher-priority arrival
that outranks a running task by more than the hysteresis margin calls
`request_cancel` on its token.

## Cooperative cancellation

A concrete `threading.Event`-backed `CancelToken` (ADR-0167) satisfies the L3
`CancelToken` Protocol (`is_set` + `request_cancel`). Capacity bodies receive a
read-only `CancelTokenView` and poll it at yield points; `stop("abort")` calls
`request_cancel` on all in-flight tokens.

## Signal-triage worker

An always-on dedicated thread (ADR-0169) classifies incoming signals into the
four tiers. At Phase 46 it runs a tier-passthrough stub; the L3
`decision.signal_to_tier` capacity replaces it at Phase 47.

## Monitor subscription registry

A session-scope `Dict[DataState IRI, List[Monitor IRI]]` (ADR-0168) built by
inverting each Monitor's `subscribes_to`, consuming `cl.iter_monitors()`.
Register/unregister are orchestrator-thread-only.

## ALS subsystem registry

The L4-owned registry of ALS subsystem registrations (Chat A D9.1). The shape is
fixed; the v1 catalog is empty (the concrete subsystems ship with WSD
installation). All registration IRIs point to L3 capabilities.

## Dream-cycle timer

A periodic timer (ADR-0162 / ADR-0165) that, with the MM deep-copy primitive
(`fork_dream_mm`), supports dream-as-live re-execution. At Phase 46 the timer
mechanism and the deep-copy primitive ship; the dream driver it ticks — invoke
dream bodies, drive live re-execution, fire ALS signals, consume replan-injection
directives — lands at Phase 47/48.
