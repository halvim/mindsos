---
title: Capacity Layer — internals (halvim)
last_confirmed_phase: 33
---

# Capacity Layer — internals (halvim)

This page documents halvim's `mindsos_capacity` package internals.
Parent tree (`/Layered Intelligence/docs/dev/internals/capacity.md`)
holds the canonical cross-layer contract; halvim's page covers the
package-local details + Phase-by-phase divergences (Model C — halvim
and parent share design intent; halvim diverges in implementation
detail where noted).

## L3 write capacities — symmetric invocation contract (Phase 33; ADR-0146)

Phase 33 ships the L3 write-capacity surface (per ADR-0145 +
ADR-0146 + ADR-0143 + ADR-0147) with a stub-phase carve-out
documented in ADR-0146 §amendment-1. The summary:

### Return contract — target shape

Per ADR-0146 §Decision, L3 write capacities return:

```python
WriteOutcome = Union[WriteResult, ProblemTraceRecord]
```

Successful writes return `WriteResult(iri, role, scope, written_at,
extras)`. Business-logic failures (validator failure, L1 reject,
capability denial) return `ProblemTraceRecord(kind="...", ...)`.
Programmer error + infrastructure failure propagate as Python
exceptions through `runtime.invoke`'s envelope.

The contract is *symmetric* with read capacities — neither raises for
implementation/business failures; L4's orchestrator handles all
failures via the same `InvocationResult` envelope shape.

### Phase 33 stub-phase carve-out

ADR-0146 §amendment-1 enumerates 5 clauses. Summary:

1. **Stub-phase failures raise; envelope catches.** Phase 33 capacity
   bodies do NOT return `ProblemTraceRecord` — both failure modes
   raise (`WriteHandleNotWiredError` from the handle stub;
   `CapabilityDeniedError` from in-body cap-checks).
   `runtime.invoke` envelopes as `success=False, error=<type>`.
2. **Session routing via `context["session"]`.** `CapacityLayer.invoke`
   + `.start_resident` inject the session object into the context dict
   alongside `session_user_id` + `session_id`. Capacity bodies extract
   via `(context or {}).get("session")`.
3. **Input shapes deferred via opaque placeholder DataStates.**
   `datastate:mm.composite_instance` + `datastate:problem_trace.record`
   are opaque-tag placeholders. Phase 34 / first L4 flow tightens.
4. **Write capacities have `outputs=()` (pipeline terminators).** They
   consume but emit nothing into the DataState flow graph. Phase 30's
   BFS pipeline-finder skips them as dead-ends; L4 invokes writes
   directly.
5. **`KLWriteHandle` stub-phase home is L2** at
   `mindsos_knowledge/write_handle.py`. `writeable()` returns a real
   handle; `metagraph()` returns the real L1 Metagraph; `graph()` +
   `mint_iri()` + `validate_node()` + `validate_xref()` raise
   `WriteHandleNotWiredError`. Phase 34 wires `graph()` + `mint_iri()`;
   Phase 36 wires the two validator methods.

### Phase 33 shipped capacities

- `capacity:consolidate:mm` (`mindsos_capacity/builtins/consolidate.py`)
  — Local write to `memories` role-graph; first occupant of the new
  `CATEGORY_CONSOLIDATE` category.
- `capacity:trace:problem` (`mindsos_capacity/builtins/trace.py`) —
  Global write to `problem-trace` role-graph; first *write* occupant of
  the existing `CATEGORY_TRACE` category.

Both expose idempotent installers
(`install_consolidate_capacities(layer)` +
`install_trace_capacities(layer)`) following Phase 31's
`install_text_capacities` partial-state-detection precedent.

### Phase 34 handover

Phase 34 (ADR-0146 §Implementation criterion (b)) wires the working
handle bodies + capacity success paths. Deletion targets:

- The `raise WriteHandleNotWiredError` lines in
  `KLWriteHandle.graph()` + `.mint_iri()`.
- The `raise AssertionError("unreachable at Phase 33")` placeholder
  lines in `capacity:consolidate:mm` + `capacity:trace:problem`
  bodies (replaced with the actual `WriteResult` return path).

`CapabilityDeniedError`'s in-body raise may also shift to return
`ProblemTraceRecord(kind="CAPABILITY_DENIED")` at Phase 34+ per
ADR-0146 §Decision target; that decision is left to the Phase 34
chat.

## See also

- ADR-0145: L3 per-target write capacity categories.
- ADR-0146: L3 symmetric write invocation contract.
- ADR-0143: KLWriteHandle pattern for L3 write capacities.
- ADR-0147: Per-flow build pattern for L3 write capacities.
- `docs/dev/coordinated-changes/L3-capacity-write-flows.md` — per-flow
  tracker (which capacity is built, deferred, or in-progress).
- Parent tree `docs/dev/internals/capacity.md` — canonical
  cross-layer contract.
