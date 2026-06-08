---
title: Write-body capability gating — boundary resolution (ADR-0146 / ADR-0159)
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L4
related: [0146, 0159, 0010]
---

# ADR-0170: Write-body capability gating — boundary resolution

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0146 (write-body capability gating — the policy this resolves the home for), ADR-0159 (capacity registration contract v2 — the `CapacityContext` that deliberately omits a session field), ADR-0010 (domain layers do not import Server).

## Context

ADR-0146 requires that a capacity which **writes** (e.g. L2 mutations) be capability-gated against the acting session. ADR-0159 (Phase 42) shipped a frozen 10-field `CapacityContext` that carries `session_id` and `user_id` (string identifiers) but **no capability/authorization handle** — the body knows *who* it runs for but not *what that principal is permitted to do*. The granted-capability set is held Server-side, not in the body context. So the question Phase 42 carried forward (PB-23 part ii): where does the write-body capability gate live, given the body cannot resolve authorization from its context?

This is L4-substrate territory because the only thing that invokes a write-body holding the live session (and thus the granted-capability set) is the L4 runtime.

## Decision

### 1. The gate lives in L4 dispatch, not in `CapacityContext` (PB-5)

The write-body capability check is performed by **L4 at the dispatch boundary**, before a write-capable capacity is submitted to the worker pool. The `IntelligenceLayer` (one per session) holds the live session and its granted-capability set; dispatch checks the capability required by the capacity's declared `effect_iri` (ADR-0159) against that set, and rejects the invocation if the session lacks it. The `CapacityContext` handed to the body stays **authorization-free** — it carries `session_id`/`user_id` for provenance but no capability handle, so the L3 body never sees auth state, preserving the Chat A strict line (decisions/effects are declared in L3; *authorization* is an L4 control-flow concern) and ADR-0010 (domain layers, including L3 capacity bodies, do not reach into Server/session concerns).

### 2. Contract now, migration + enforcement at Phase 47

Phase 46 ratifies this **boundary contract** (gate lives in L4 dispatch, reads the session-held capability set, checks `effect_iri`). The implementation — `runtime.invoke` building a `CapacityContext`, the body migration, and live gate enforcement — all land at **Phase 47**, where the orchestrator first dispatches real capacities under a session (the true consumer). Grounding at Phase 46 R1 showed `invoke`'s `context: Optional[Mapping[str, Any]]` is a **shipped public signature consumed by the entire test corpus**; flipping it is a corpus-wide atomic change, not a mechanical body edit, and has no Phase-46 caller (the lifecycle roundtrip invokes nothing). Per consumer discipline it moves to its caller's phase.

### 3. Body migration scope

`consolidate` (`builtins/consolidate.py:136`) and `trace` (`builtins/trace.py:119`) are the only `context.get("kl")` users (grounding-confirmed; the `text.*` body named in PB-23 does not access `kl`). Both migrate to `context.kl` at **Phase 47** alongside the `invoke` signature change, since the body and its new caller move together.

## Rationale

- **Authorization is control flow, not a capability decision.** Keeping it in L4 dispatch (not in the L3 body context) honours the strict line and ADR-0010, and avoids widening the just-frozen 10-field `CapacityContext`.
- **Gate at dispatch reads `effect_iri`** — the declared write effect (ADR-0159) is exactly the capability surface to check; no new declaration needed.
- **Defer enforcement to its consumer.** No L4 path dispatches a write-body under a session until Phase 47; the contract is fixed now so Phase 47 implements against it.

## Consequences

- `CapacityContext` stays at 10 fields, session-free (no churn to the Phase-42 frozen shape).
- Phase 46 closes the *mechanical* half of PB-23 (`invoke`→`CapacityContext`, body `context.kl` migration).
- Phase 47 implements the dispatch-boundary gate (reads session from `IntelligenceLayer`, checks `effect_iri` capability).
- Amends ADR-0146 (gate location = L4 dispatch) and ADR-0159 (confirms the session-free context is intentional, not an omission).

## Alternatives considered

1. **Add a `session`/capability handle to `CapacityContext`.** Rejected — widens the frozen 10-field context the moment after it shipped; leaks auth state into L3 bodies (violates the strict line + ADR-0010); the field would ship unconsumed until Phase 47.
2. **Gate inside each write-body.** Rejected — duplicates the check across bodies; puts authorization logic in L3 where it doesn't belong.
3. **Enforce at Phase 46.** Rejected — no session-dispatching consumer until Phase 47; dead code.

## §v2-reservations

- (none.)

## §Implementation (Phase 46 — convergence; pending ship)

Phase 46 ships **this ADR only** (the boundary contract) + the ADR-0146/0159 amendment footers. The `invoke`→`CapacityContext` signature change, the `consolidate`/`trace` body migration, and the dispatch-boundary gate enforcement all land at **Phase 47** (grounding-driven defer; their caller is the Phase 47 orchestrator). PB-23 closes at Phase 47, not 46.
