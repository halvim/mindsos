---
title: TierEnum home (L3) + signal-triage worker thread placement
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L3+L4
related: [0159, 0163, 0168, 0155]
---

# ADR-0169: TierEnum home (L3) + signal-triage worker thread placement

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0159 (capacity registration contract v2 — `context.py` verdict types, including `TierVerdict`), ADR-0163 (Executor — imports `TierEnum` downward), ADR-0168 (MonitorSubscriptionRegistry — supplies the Monitors triage fires), ADR-0155 (Monitor relocation).

## Context

Chat A D32.2 = A settled an **always-on dedicated signal-triage thread** that classifies signals into the 4 priority tiers and surfaces CRITICAL signals to the orchestrator's next yield. The classifier itself is an L3 capacity, `decision.signal_to_tier(signal) -> tier` (Chat A L3-list). Chat A also noted the tier enum is "shared with the L3 classifier, lives in a shared module."

This raises a layer-placement question. The Executor (ADR-0163, L4) needs the `TierEnum`; the classifier (`decision.signal_to_tier`, L3) returns it. **L3 must not import L4** (upward-import violation, enforced by `tests_server/integration/test_layer_isolation.py` + the phase_16/phase_28 import-isolation suites). The R0 grounding probe found the resolution already anticipated in shipped code: `mindsos_capacity/context.py` ships `TierVerdict` with `tier: Optional[Any]` and the docstring *"the downstream TierEnum (typed `Any` here pending its owning family)."* Phase 42 deliberately left the enum's home open; this ADR fixes it.

## Decision

### 1. `TierEnum` + defaults live in L3 `mindsos_capacity` (PB-8)

The `TierEnum` (CRITICAL / FOREGROUND / BACKGROUND / DREAM), the per-tier default `attention_score` table (1000 / 500 / 100 / 10), and the hysteresis default `H = 50` are defined in `mindsos_capacity` (a new `tiers.py`, or extending `context.py` beside the verdict types). The L3 classifier imports them locally; the L4 Executor (ADR-0163) and signal-triage thread import them **downward**. This satisfies layer isolation — there is no upward dependency.

### 2. Narrow `TierVerdict.tier`

`TierVerdict.tier` is narrowed from `Optional[Any]` to `Optional[TierEnum]`, closing the Phase-42 "pending its owning family" placeholder. Small additive change to a shipped L3 module.

### 3. Signal-triage thread is L4, with a v1 passthrough stub classifier (PB-7)

`mindsos_intelligence/signal_triage.py` runs the always-on dedicated thread (the thread is L4 substrate per Chat A "L4 retains"). At Phase 46 the classifier capacity `decision.signal_to_tier` is an L3 skeleton not yet shipped, so the thread calls a **tier-passthrough stub** — it reads a tier hint carried on the (test) signal and routes accordingly — so the signal→tier→queue path is genuinely exercised. The stub is replaced by the real L3 `decision.signal_to_tier` invocation at **Phase 47**.

A constant-tier fallback (e.g. always FOREGROUND) was rejected: it would mean CRITICAL signals never surface and the classification-path test would be vacuous.

## Rationale

- **Decisions are L3 (strict line); the tier vocabulary the decision returns must therefore be L3-reachable.** Placing the enum in L4 would force an upward import the gate forbids. The shipped `TierVerdict` placeholder confirms this was always the intent.
- **Thread in L4, verdict in L3.** The thread is pure substrate (control flow); the classification *decision* is L3. The passthrough stub keeps the substrate testable end-to-end without pre-shipping the Phase 47 capacity.

## Consequences

- New L3 `mindsos_capacity` surface: `TierEnum` + default tables; `TierVerdict.tier` narrowed. (Bundled into PR-A; small L3 edit.)
- New L4 `mindsos_intelligence/signal_triage.py` (thread + stub classifier).
- ADR-0163's Executor + ADR-0168's triage routing both depend on this enum.
- Phase 47 swaps the stub for `decision.signal_to_tier`.

## Alternatives considered

1. **TierEnum in `mindsos_intelligence` (L4).** Rejected — L3 classifier can't import it; fails layer-isolation gate.
2. **TierEnum in `mindsos_core` (L1).** Rejected — tiers are a scheduling/decision concept, not a core graph primitive; L3 is the natural home beside `TierVerdict`.
3. **Constant-FOREGROUND stub classifier.** Rejected — CRITICAL never surfaces; vacuous test.
4. **Defer the whole signal-triage thread to Phase 47.** Considered (PB-0 Opt C); rejected — the thread is substrate Chat A lists under "L4 retains"; the passthrough stub makes it testable now.

## §v2-reservations

- (none — `decision.signal_to_tier` is scheduled for Phase 47, not reserved.)

## §Implementation (Phase 46 — convergence; pending ship)

PR-A (L3 part): `TierEnum` + defaults in `mindsos_capacity`; narrow `TierVerdict.tier`. PR-B (L4 part): `mindsos_intelligence/signal_triage.py` (thread + passthrough stub). Test `tests/phase_46/test_signal_triage_worker.py` (always-on thread + classification path via the stub). Real classifier wiring at Phase 47.
