---
title: Monitor lifecycle relocated from L3 to L4 substrate
status: Accepted
date: 2026-06-01
layer: L3
supersedes: [ADR-0073]
aliases: [reframe-D36, L3-2]
---

# ADR-0155: Monitor lifecycle relocated from L3 to L4 substrate

**Status:** Accepted

**Date:** 2026-06-01

## Context

Phase 31 (2026-05-25) shipped Monitor lifecycle plumbing on `CapacityLayer`: `start_resident()`, `stop_resident()`, `active_subscriptions()`, the per-layer `_subscriptions: Dict[str, ResidentSubscription]` field, the `ResidentSubscription` dataclass, and `ResidentError`. Per ADR-0073 + §amendment-1, the design is "descriptive only — L4's event loop iterates `active_subscriptions()` and dispatches." But the subscription registry and the lifecycle methods are L3-owned state.

Chat B (2026-05-31) ratified three invariants that jointly forbid this:

- D-B13 — L4 invariant: no shadow state outside MM. `_subscriptions` is shadow state at L3.
- D-B15 — "L3 owns capacities only; threads are L4." Lifecycle methods imply thread-coordination policy.
- D-B38 — orchestration *runtime state* (SCMSState, MSURLedger) lives in intelligence-MM; *capacity invocations* live as CapacityInstances in capacity-MM. Monitor runtime state belongs at L4.

WSD §6.3 (`coordinated_change_L3` 2026-04-29) independently proposes "descriptive-only L3 Monitors + L4 owns lifecycle." Chat A R6 (D36) ratified directional preference for retirement; this ADR ratifies the supersession.

## Decision

Retire from L3 (`CapacityLayer` + `mindsos_capacity.runtime` + `mindsos_capacity.exceptions`):

- `CapacityLayer.start_resident()`, `stop_resident()`, `active_subscriptions()` methods.
- `CapacityLayer._subscriptions: Dict[str, ResidentSubscription]` field.
- `ResidentSubscription` dataclass (`runtime.py`).
- `ResidentError` exception (`exceptions.py`).
- `KIND_RESIDENT` constant — renamed to `KIND_MONITOR` (`identifiers.py:138`).

Keep at L3:

- `Monitor` subclass of `_CapacityBase` (registered via `register_capacity` like any capacity).
- `Monitor.subscribes_to: Tuple[str, ...]` — **DataState IRI semantics** (Phase 31 shipped form; WSD `coordinated_change_L3` `subscribes_to: list[capacity_iri]` wording is shorthand and translates to DataState IRIs at WSD installation chat authoring time).
- `Monitor.node_kind = KIND_MONITOR` (renamed).
- New `cl.iter_monitors() -> List[Monitor]` helper — Local-wins merged enumeration mirroring `_resolve_declaration`.

L4 substrate (downstream) owns:

- `MonitorSubscriptionRegistry` — session-scope `Dict[DataState IRI, List[Monitor IRI]]` built from `cl.iter_monitors()` at session start.
- Per-task lazy Monitor `CapacityInstance` instantiation via `mm.get_or_instantiate(capacity_iri)`.
- Orchestrator-thread-only register/unregister discipline (formerly Chat A R1 D32.4 resident-clarification scope).
- SCMSState + MSURLedger composites in intelligence-MM per Chat B D-B38.

Public export hard-break for `KIND_RESIDENT`, `ResidentSubscription`, `ResidentError` from `mindsos_capacity/__init__.py` `__all__`, gated by R0 audit (no external consumers expected).

## Consequences

**Good:**

- Chat B invariants satisfied; zero shadow state at L3.
- L3-Q1 resolved: no L3-internal residents; Monitors and "residents" collapse to one concept.
- WSD installation chat receives uniform Monitor authoring shape; lifecycle plumbing is L4 substrate's job.
- Phase 31 test suite (~6-8 files) retires whole.

**Cost:**

- Hard-break for three public symbols (audit-gated; coordinated with ADR-0156 hard-break audit per consolidated R0 audit pass).
- WSD `coordinated_change_L3` `subscribes_to: list[capacity_iri]` wording requires translation rule at authoring; documented as "capacity-IRI shorthand → DataState IRI" in the WSD installation chat brief.
- Tests/phase_27 + tests/phase_28 dataclass/register tests need `node_kind="monitor"` rename (~2 file edits).

## Alternatives considered

1. **A — Full retire of Monitor subclass** (merge into Capacity with `mode` flag) — rejected: loses Phase 27 authoring-time clarity (Capacity/Monitor/Adapter triad); mode-flag is a hidden contract authors must remember.

2. **C — Subscription as new IntergraphEdge type at L3 type-graph** (`subscribes_to` edges from DataState → Monitor) — rejected: third edge type at L3 violates Chat B D-B46 v1 edge catalog lock; conflates event-time trigger with structural relation.

## Supersession trail

- Supersedes **ADR-0073** ("Residents are descriptive; L3 contains no event loop") + **ADR-0073 §amendment-1** ("Halvim divergences — per-layer subscription registry; subscribes_to kwarg dropped; eq=False handle; ResidentError carve-out").

## Sequencing

Ship phase **X2** — between ADR-0157+ADR-0158 (X1) and ADR-0156+ADR-0159 (X3). Independent of D38 bipartite reframe; structurally smaller; retires ~100 LOC of resident infrastructure that ADR-0156 author would otherwise have to mentally bracket.

## Rationale

Per-decision rationale, alternatives explored, and 3-round saturation history at `docs/_workbench/L1_L3_REFRAME_DECISIONS.md` §D36.
