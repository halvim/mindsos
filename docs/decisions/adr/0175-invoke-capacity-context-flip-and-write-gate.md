---
title: invoke→CapacityContext flip + write-body capability gate enforcement
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L4
related: [0146, 0159, 0170, 0171]
---

# ADR-0175: `invoke`→CapacityContext flip + write-body gate enforcement

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0146 (write-body capability gating policy), ADR-0159 (CapacityContext v2), ADR-0170 (gate boundary — contract this enforces), ADR-0171 (orchestrator — the dispatching consumer).

## Context

ADR-0170 fixed the boundary contract (write-body capability gate lives in L4 dispatch, reads `effect_iri` against the session capability set; `CapacityContext` stays authorization-free) but **deferred the implementation to Phase 47**, where the orchestrator first dispatches real capacities under a session. Two coupled changes were carried: (i) flip `runtime.invoke`'s `context: Optional[Mapping[str, Any]]` to a typed `CapacityContext`; (ii) enforce the gate. PB-23 has been carried since Phase 42.

Phase 47 grounding (call-site census) sized the blast radius: only `consolidate.py:136` + `trace.py:119` read `context.get("kl")`; the `capacity_layer` write-path (`context["kl"]`); `runtime.py:218` (`call_capacity(…, context=context)`); and two session-injection tests (`tests/phase_30`, `tests/phase_33`). Well within a hard flip.

## Decision

### 1. Hard flip `invoke`→CapacityContext (PB-1)

`runtime.invoke` and `capacity_layer.invoke` change `context` from `Optional[Mapping[str, Any]]` to `Optional[CapacityContext]`. The **caller builds the CapacityContext** (`invoke` only threads it — it has no session/mm_handle to construct one). `consolidate`/`trace` bodies migrate `context.get("kl")` → `context.kl`. The two session-injection tests migrate from ad-hoc dict keys (`{"session_user_id": …}`, `{"session": sentinel}`) to building a `CapacityContext` (whose `session_id`/`user_id` are already typed fields). No transitional union type — the dual contract PB-23 exists to remove is not reintroduced.

### 2. Canonical builder + gate in `dispatch.py` (PB-2 / PB-D)

A new `mindsos_intelligence/dispatch.py` is the single L4 choke point: it builds the `CapacityContext` (session_id/user_id from `IntelligenceLayer`, mm_handle, cancel_token view, learned_parameters_snapshot, version_snapshot, kl/cl handles) and, **before submitting a write-body capacity** (zero declared outputs, ADR-0146), checks the capability required by the declared `effect_iri` (ADR-0159) against the session's granted-capability set held by `IntelligenceLayer`; rejects if absent. All orchestrator capacity calls route through it; the migrated tests use it as the canonical builder.

**Capability-set source:** the granted-capability set is Server-owned (ADR-0010 — L3 must not reach Server; L4 may). If Server-session capability wiring is not yet threaded into `IntelligenceLayer` at Phase 47, the gate checks against a capability set passed at `start()` (present-or-absent); the real catalog is Server/WSD. The gate **mechanism** is enforced at 47 regardless.

### 3. Enforced at 47 + synthetic test (PB-D)

The only production write-body (consolidation) is a Phase-47 stub, so there is no production write-body-under-session traffic at 47. The gate is nonetheless **enforced at 47** (per ADR-0170 §Decision-2) and covered by a **dedicated synthetic test**: a throwaway write-body capacity dispatched with and without the required capability. A self-contained, testable contract clears the consumer-discipline bar ("ship ahead of consumer only if testable").

## Rationale

- **Hard flip** closes PB-23 for good — no lingering dual context contract.
- **Single dispatch choke point** co-locates context-building and the gate; L3 bodies stay authorization-free (strict line + ADR-0010).
- **Enforce + synthetic test** honors ADR-0170's 47 commitment without a third PB-23 slip, and is testable so it is not dead-shipped.

## Consequences

- `runtime.invoke` / `capacity_layer.invoke` signatures change (corpus-wide; test-fixture migration sized small by the census).
- `consolidate`/`trace` bodies read `context.kl`; PB-23 **closes at Phase 47**.
- `dispatch.py` lands in the S12 commit so migrated tests use the canonical builder.
- Amends ADR-0146/0159/0170 §Implementation footers to "enforced at Phase 47".

## Alternatives considered

1. **Transitional union (`Mapping | CapacityContext`) + body shim (PB-1 Opt B).** Rejected — keeps the dual contract; bodies need isinstance branching.
2. **Gate inside `runtime.invoke` (L3).** Rejected — L3 has no session/capability handle (the reason ADR-0170 put it in L4).
3. **Defer enforcement to Phase 48 (real write-body consumer).** Rejected — third PB-23 slip; contradicts ADR-0170; the gate is testable now via a synthetic write-body.

## §v2-reservations

- Thread the real Server-session granted-capability set into `IntelligenceLayer` (currently present-or-absent set at `start()`).

## §amendment-1 (Phase 47 grounding — read/write split)

Grounding the write-bodies at Phase 47 (PR-A) revealed the R0 census undercounted: `consolidate`/`trace` not only read `context.get("kl")` but read `context.get("session")` and call `kl.writeable(session, …)` + `session.has(CAN_WRITE_GLOBAL)` — they need the **Session object** to perform the KL write. A truly authorization-free `CapacityContext` (no session object) is therefore unreachable without also refactoring `kl.writeable`'s signature (an L2 `mindsos_knowledge` change), far beyond this phase. And consolidation is **stubbed at Phase 47** (ADR-0171 §4), so the write-bodies have **no Phase-47 orchestrator consumer** — their real consumer is wired consolidation at Phase 48.

**Decision (user-ratified): split S12 by read/write.**

- **Phase 47 (this phase):** (a) widen `runtime.invoke` / `call_capacity` `context` annotation to the transitional `Optional[Union[Mapping, CapacityContext]]`; (b) ship the new L4 `dispatch.py` (CapacityContext builder + `effect_iri` write-gate, authoritative, synthetic test); (c) dispatch the v0 **read** capacities (planning/phase1/orchestration) through it with a `CapacityContext` (these need no session). **Leave `capacity_layer.invoke`'s dict+session write path and the `consolidate`/`trace` bodies untouched.**
- **Phase 48:** migrate `consolidate`/`trace` off dict `context` + resolve the authorization-free-vs-`kl.writeable(session)` tension when consolidation is wired (its real consumer); drop the transitional union annotation.

PB-23's **read half closes at 47**; its **write half closes at 48**. ADR-0170 §Decision-1's "authorization-free context" is preserved for the *read* path now; the write-path reconciliation (whether the principal lives on the context, or L4 performs the gated write) is deferred to Phase 48 with the real consumer.

## §Implementation (Phase 47; pending ship)

PR-A ships: `runtime.py` + `capacity.py` annotation widening (transitional union); `_CapacityBase.placeholder` marker; `mindsos_capacity/builtins/{planning_v0,phase1_v0,orchestration_v0}.py` (read v0 catalogs); `mindsos_intelligence/dispatch.py` (builder + `effect_iri` gate); `tests/phase_47/` (v0 catalogs + synthetic gate). The `consolidate`/`trace` body migration + `tests/phase_30`/`phase_33` migration move to **Phase 48** per §amendment-1.

## §amendment-2 (Phase 48 — write-half closed via ADR-0180)

The §amendment-1 open question (principal-on-context vs L4-performs-write) is resolved at Phase 48 by **ADR-0180**: L4 `dispatch.py` injects a **pre-authorized, session-bound `writeable` capability** (an 11th `CapacityContext` field) for write-bodies; bodies call `context.writeable(role, scope, version)` → handle → `validate_node` + `write_and_validate` (ADR-0146 contract unchanged). The capability check fires **at write-time inside the L4 callable**, scope-aware (`local` → none; `global` → `CAN_WRITE_GLOBAL`) — superseding the Phase-47 `check_write_permitted` pre-gate for write-bodies. Both `consolidate` and `trace` migrate off the dict path to `context.writeable`; production dispatches them via `L4Dispatcher`. **PB-23's authorization (write) half closes at Phase 48.** No `_CapacityBase` change; ADR-0170 §Decision-1's authorization-free context is preserved (the context carries a narrowed capability, not a principal).

**A1 deferral (user-ratified, Phase 48 R1).** Dropping the transitional `Optional[Union[Mapping, CapacityContext]]` annotation requires `capacity_layer.invoke` (which serves the entire read-capacity corpus) to stop emitting dict context — pulling every read test into the blast radius mid-convergence. The union annotation + the read-path dict are therefore **kept one more phase** as documented read-legacy; the cosmetic union-drop is deferred to a cleanup pass. `tests/phase_30` + the `tests/phase_33` context-injection tests are **not** migrated at Phase 48 (`capacity_layer.invoke` unchanged). See ADR-0180 §3.
