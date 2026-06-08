---
title: MonitorSubscriptionRegistry — L4-side Monitor lifecycle
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L4
related: [0155, 0169, 0166]
---

# ADR-0168: MonitorSubscriptionRegistry — L4-side Monitor lifecycle

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0155 (Monitor lifecycle relocated from L3 to L4 — this is the L4 side), ADR-0169 (signal-triage — routes signals to subscribed Monitors), ADR-0166 (MM instantiation — Monitor instances live in capacity-MM).

## Context

ADR-0155 (Phase 41) retired Monitor lifecycle from L3: `start_resident`/`stop_resident`/`active_subscriptions` were removed and replaced by a producer, `cl.iter_monitors() -> List[Monitor]`, with **no v1 consumer** — the consumer is the L4 substrate, deferred to Phase 46. The L1/L3 reframe constrained the L4-side shape (§D36): a session-scope `Dict[DataState IRI, List[Monitor IRI]]`. The R0 grounding probe confirmed a `Monitor` declares the DataStates it watches via a `subscribes_to` tuple of DataState IRIs.

## Decision

### 1. Session-scope registry, built by inverting `subscribes_to`

`mindsos_intelligence/monitor_subscription.py` holds a per-session `MonitorSubscriptionRegistry`: `Dict[DataState IRI, List[Monitor IRI]]`. It is populated by consuming `cl.iter_monitors()` and **inverting each Monitor's `subscribes_to`** — for every DataState IRI a Monitor subscribes to, the Monitor's IRI is appended to that DataState's list. (Local-wins inheritance is already resolved inside `iter_monitors`.)

### 2. Per-task lazy Monitor instantiation

A Monitor's `CapacityInstance` is materialised lazily — instantiated into capacity-MM (ADR-0166) the first time its subscribed DataState is touched within a task, not eagerly at session start. One Monitor instance per capacity-IRI per session (the resident-uniqueness constraint, now expressed as instance identity).

### 3. Orchestrator-thread-only register/unregister

`register`/`unregister` on the registry MUST run on the orchestrator thread, never a worker (the explicit successor to the Phase-31 implicit serialization; Chat A D32.4 resident clarification). Reads (lookup by DataState IRI, used by signal-triage) are concurrent-safe.

### 4. Scope at Phase 46

Phase 46 ships the registry + the `iter_monitors` inversion + lazy instantiation hook + the thread-discipline. The thing that *drives* lookups — signal routing during a running task — is the Phase 47 orchestrator + the signal-triage classifier (ADR-0169). At 46 the registry is exercised by its own test (build from a fake CL's monitors; assert the inverted map + thread-guarded mutation).

## Rationale

- **Invert `subscribes_to`** is the natural index for the triage hot path: given a changed DataState, find the Monitors to fire. Building it once per session is cheap.
- **Lazy instantiation** keeps the no-shadow-state invariant (ADR-0165) and avoids materialising Monitors a task never triggers.
- **Orchestrator-thread-only mutation** removes the need for a registry write lock and matches the resident-serialization contract.

## Consequences

- New `mindsos_intelligence/monitor_subscription.py`; consumes the Phase 41 `cl.iter_monitors()` (closes its consumer gap).
- Signal routing (ADR-0169) reads this registry at Phase 47.
- No change to L3 — the producer already shipped.

## Alternatives considered

1. **Keyed by Monitor IRI (not DataState IRI).** Rejected — inverts the triage hot path (would scan all Monitors per signal); §D36 mandates DataState-keyed.
2. **Eager Monitor instantiation at session start.** Rejected — materialises unused state; violates lazy/no-shadow-state.
3. **Allow worker-thread register/unregister with a lock.** Rejected — re-introduces the concurrency hazard the orchestrator-thread-only rule removes.

## §v2-reservations

- (none — the contract is fully specified by §D36.)

## §Implementation (Phase 46 — convergence; pending ship)

PR-A: `mindsos_intelligence/monitor_subscription.py` (registry + `subscribes_to` inversion + lazy-instantiation hook + thread guard). Test `tests/phase_46/test_monitor_subscription_registry.py` (session-scope registry + `cl.iter_monitors()` consumption + inversion correctness + orchestrator-thread guard). Signal-driven lookup lands Phase 47.
