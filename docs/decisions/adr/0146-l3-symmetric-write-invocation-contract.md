---
title: L3 symmetric write invocation contract
status: Accepted
date: 2026-04-27
layer: L3
---

# ADR-0146: L3 symmetric write invocation contract

**Status:** Accepted (flipped Proposed → Accepted at Phase 33, 2026-05-26;
halvim; see §amendment-1 + §Implementation footer)

**Date:** 2026-04-27

**Related:** ADR-0060 (L3 fixed-not-learned), ADR-0145 (per-target write categories), ADR-0143 (`KLWriteHandle`), ADR-0139 (hybrid invariant home).

## Context

L3 ships an invariant for read/transform capacities: `invoke()` never raises for implementation errors — exceptions become `ProblemTraceRecord` records that L4 consumes as data. ADR-0138 introduces write capacities; their invocation contract has to land somewhere, and the choice between "match the read contract" vs "raise on failure" affects every write capacity built going forward.

## Decision

**Write capacities follow the symmetric (no-raise) contract.**

- **Inputs:** typed, DataState-shaped per L3's existing pattern. Session is passed explicitly: `def capacity_consolidate_mm(session: SessionProtocol, mm: CompositeInstance) -> WriteResult | ProblemTraceRecord`.
- **Successful output:** `WriteResult` dataclass with at minimum the new IRI(s) and any side-effect metadata (audit timestamps, etc.).
- **Failure output:** `ProblemTraceRecord` with structured violation details, returned (not raised). Failure modes include validator failure (KL semantic invariants per ADR-0139), L1 `XRefIntegrityError` / `SchemaViolationError` (caught and wrapped), capability denial.
- **Capability check:** at capacity entry; re-checked at `KLWriteHandle` methods that need it. Capability denial is a `ProblemTraceRecord` with `kind="CAPABILITY_DENIED"`.
- **L1 raises that escape:** programmer error (writing to a graph the handle doesn't reference, calling a primitive with wrong types). These are bugs; they propagate as Python exceptions and crash the capacity invocation. L4 sees them as `invoke()` failures.

### Skeleton

```python
@dataclass(frozen=True)
class WriteResult:
    iri: str
    role: RoleName
    scope: Literal['local', 'global']
    written_at: datetime
    extras: dict[str, Any] = field(default_factory=dict)

def capacity_consolidate_mm(
    session: SessionProtocol,
    mm: CompositeInstance,
) -> WriteResult | ProblemTraceRecord:
    if not session.has_capability(CAN_WRITE_LOCAL_EPISODIC_MEMORIES):
        return ProblemTraceRecord(kind="CAPABILITY_DENIED", ...)
    handle = kl.writeable(session, role=ROLE_EPISODIC_MEMORIES, scope='local')
    iri = handle.mint_iri(type_="Episode", user_id=session.user_id, episode_id=mm.root_id)
    if not (vr := handle.validate_node(value=mm.summary, type_="Episode")).ok:
        return ProblemTraceRecord(kind="VALIDATION_FAILED", violation=vr, ...)
    try:
        handle.graph().add_node(node_id=iri, value=mm.summary, type_="Episode")
        # ... XRefs, properties ...
    except (XRefIntegrityError, SchemaViolationError) as exc:
        return ProblemTraceRecord(kind="L1_REJECTED", exc=exc, ...)
    return WriteResult(iri=iri, role=ROLE_EPISODIC_MEMORIES, scope='local', written_at=now())
```

### Failure-mode table

| Failure | Handling |
|---------|----------|
| Capability denied | `ProblemTraceRecord(kind="CAPABILITY_DENIED")` |
| KL semantic validator failure | `ProblemTraceRecord(kind="VALIDATION_FAILED", violation=...)` |
| L1 structural error (XRef, schema, reserved key, dup id) | catch, wrap as `ProblemTraceRecord(kind="L1_REJECTED")` |
| L1 OCC version mismatch | retry with current state up to N times; final failure → `ProblemTraceRecord(kind="OCC_RETRIED_OUT")` |
| Programmer error (wrong type, wrong graph) | propagate Python exception; this is a bug |
| Server / network error | propagate Python exception; this is infrastructure |

## Rationale

L3's existing read/transform capacities don't raise; they return data describing failure. L4's orchestrator already knows how to consume `ProblemTraceRecord` values. Asymmetric contract (writes raise, reads return) would force L4 to fork its handling per capacity kind — wrong direction.

`ProblemTraceRecord` is a write-side capacity output too: the `capacity:trace:record-problem` capacity *writes* a `ProblemTraceRecord` to the `problem-trace` role-graph. Symmetric contract makes this loop natural — failed writes produce records of the same shape that get written by the trace capacity.

L1 errors that escape (programmer bugs) are not first-class data because the capacity author wrote wrong code. Wrapping every Python exception as `ProblemTraceRecord` would hide bugs. The line: business-logic failure → record; programmer error → exception.

## Consequences

**Good:**

- One contract across read and write capacities. L4's orchestrator handles all failures uniformly.
- Failure data is first-class; L4's confidence-tracking and replan loops feed on it.
- Capability denial, validator failure, and L1 rejection all surface through the same return shape.

**Tradeoffs:**

- Capacity authors must remember to check return type. Static type checking helps (`WriteResult | ProblemTraceRecord` union).
- Silent-failure risk: a capacity that returns `ProblemTraceRecord` but the caller ignores it is a bug. Caller side (L4 orchestrator) is responsible for handling.
- OCC retry is a capacity-side concern under this contract; bounds + back-off live in capacity code.

## Alternatives considered

1. **Strict raise on failure.** Rejected — breaks L3's no-raise pattern for reads; asymmetric handling on L4 side.
2. **Hybrid: raise on capability/validator failure (programmer error); return on data failure.** Rejected — splits "what is programmer error" hair-splittingly; capability denial is a runtime data fact, not programmer error.
3. **Return `Result[WriteResult, Failure]` algebraic type.** Considered. Type-safer than `WriteResult | ProblemTraceRecord`. Held — current Python idioms favour the union; reopen if migration to a Result library happens.

## Implementation references

- New base type alias: `WriteOutcome = WriteResult | ProblemTraceRecord` exported from `mindsos_capacity`.
- `WriteResult` dataclass: `mindsos_capacity/write_outcome.py`.
- Capacity templates: `mindsos_capacity/templates/write_capacity.py` shows the skeleton above.
- Test pattern: each write capacity tests success path + each failure mode (capability denied, validator fail, L1 reject).
- ADR moves to Accepted when (a) `WriteResult` ships, (b) the first L3 write capacity follows the contract, (c) `docs/dev/internals/capacity.md` documents the contract.

## §amendment-1 — Phase 33 stub-phase carve-out (halvim, 2026-05-26)

Phase 33 ships the write-contract surface (5-clause carve-out below) so
`capacity:consolidate:mm` + `capacity:trace:problem` can register and
invoke through the regular ADR-0072 envelope, ahead of Phase 34's
working `KLWriteHandle` body. The §Decision wording above remains the
*target* contract; Phase 33's stub-phase divergences are documented here.

**Clause 1 — Stub-phase failures raise; envelope catches.** Phase 33
write-capacity bodies do NOT return `ProblemTraceRecord` for either
failure mode. Both surface via raise + `runtime.invoke()` envelope:

- Handle-not-wired: `KLWriteHandle.graph()` (and the other stubbed
  handle methods) raise `WriteHandleNotWiredError`; envelope yields
  `InvocationResult(success=False, error=WriteHandleNotWiredError)`.
- Capability denial: bodies raise `CapabilityDeniedError`; envelope
  yields `InvocationResult(success=False, error=CapabilityDeniedError)`.

Phase 34+ may shift these to return `ProblemTraceRecord(kind=...)` per
the §Decision target once the failure-mode surface stabilises against a
real consumer.

**Clause 2 — Session routing via `context["session"]`, not positional.**
The §Decision skeleton shows `def capacity_consolidate_mm(session, mm)`
as positional. The actual invocation routing (Phase 30
`CapacityLayer.invoke` + `runtime.invoke` via `call_capacity`) forwards
`**inputs, context=context` — `session` is not in scope. Phase 33
extends `CapacityLayer.invoke` + `.start_resident` with
`ctx.setdefault("session", session)` (alongside the pre-existing
`session_user_id` + `session_id` denormalization); write-capacity
bodies extract via `context.get("session")`. Read-capacity bodies
ignore the new key; backward-compatible with Phase 30's exact-keys
assertions (which use `in` / `not in` membership).

**Clause 3 — Input shapes deferred via opaque placeholder DataStates.**
The §Skeleton's `mm: CompositeInstance` typed input cannot be matched
verbatim — halvim's `CompositeInstance` (`mindsos_instances`) lacks the
`summary` / `root_id` / `task_pattern_iri` attributes the §Skeleton
references; per-flow build (ADR-0147) defers the typed-input lock until
the L4 consolidation flow consumes the capacity. Phase 33 ships opaque
placeholder DataStates (`datastate:mm.composite_instance` +
`datastate:problem_trace.record`); capacity bodies never read the
input value (handle raises before any access). Phase 34 / first L4
flow tightens the shapes.

**Clause 4 — Write capacities have `outputs=()` (pipeline terminators).**
The §Skeleton's `return WriteResult(...)` shape doesn't fit the existing
`call_capacity` outputs-validation contract (mapping-of-declared-DS or
single-value-matching-sole-DS). Write capacities consume but emit
nothing into the DataState flow graph; they are pipeline TERMINATORS,
not flow stages. Phase 30's BFS pipeline-finder correctly treats them
as dead-ends — L4 invokes writes directly, not via pipeline discovery.
Phase 34's `WriteResult` production may either bypass `call_capacity`
via a separate write-invoke entry point or relax the output-validation
contract.

**Clause 5 — `KLWriteHandle` stub-phase home is L2 per ADR-0143.** Phase
33 ships `mindsos_knowledge/write_handle.py` + `KnowledgeLayer.writeable(
session, role, scope)` entry point. `writeable()` itself does NOT
raise — it returns a real `KLWriteHandle` with partially-stubbed methods:
`metagraph()` returns the real L1 Metagraph; `graph()` + `mint_iri()` +
`validate_node()` + `validate_xref()` raise `WriteHandleNotWiredError`.
Phase 34 (per this ADR's §Implementation criterion (b)) wires the
working bodies and deletes the raise sites in `graph()` + `mint_iri()`;
Phase 36 (ADR-0139) wires the two validator methods.

## §Implementation

**Phase 33 (halvim, 2026-05-26).** `WriteResult` dataclass + `WriteOutcome`
alias ship at `mindsos_capacity/write_outcome.py` (criterion (a) ✓).
First two L3 write capacities (`capacity:consolidate:mm` +
`capacity:trace:problem`) follow the contract via stub-phase raise
semantics per §amendment-1 clauses 1 + 4 (criterion (b) — failure-half
satisfied; success-half waits for Phase 34's body). `docs/dev/internals/
capacity.md` documents the contract in both parent and halvim trees
(criterion (c) ✓). New raisers in `mindsos_capacity/exceptions.py`:
`WriteHandleNotWiredError` + `CapabilityDeniedError` — both direct
subclasses of `CapacityLayerError`. `runtime.invoke` envelope catches
+ surfaces as `success=False, error=<type>`.

**Phase 34 (halvim, 2026-05-26) — closes clauses 4 + 5.** Wires the
KLWriteHandle body per §amendment-1 clauses 4 + 5; clauses 1, 2, 3 stay
open (per Phase 34 R0 PB-1 minimum-viable close — L4 consumer drives
the eventual flip).

- Clause 4 (outputs=() + WriteResult navigation) — closed via
  `runtime.invoke` bypass branch (Phase 34 R1 PB-A). When
  `declaration.outputs == ()`, the runtime calls the body directly,
  validates the return is `WriteResult` or `ProblemTraceRecord` (R5
  PB-G; raises `CapacityRegistrationError` otherwise), and stashes the
  typed outcome in a NEW `InvocationResult.write_outcome` field
  (additive, default `None`). Read-path callers see the existing
  `outputs: Mapping` contract unchanged.
- Clause 5 (L2 stub home) — closed by wiring `KLWriteHandle.graph()` +
  `mint_iri()` + `write_and_validate()` bodies; `validate_node` /
  `validate_xref` remain stubbed pending Phase 36 (ADR-0139).
- Clauses 1 (raise vs return-PTR), 2 (context routing — already works),
  3 (placeholder DataStates) stay OPEN per the §amendment-1 deferral
  text. Phase 34 R2 PB-A partially closes clause 3 — DataState shapes
  tighten to `ShapeDescriptor.record({"memory_id": "str", "value":
  "Any"})` for consolidate and `{"trace_id": "str", "value": "Any"}`
  for trace (the minimum surface `mint_iri` needs); L4-flow shape
  extensions stay deferred.

Capacity bodies now extract `kl` from context (R0 PB-5) alongside
`session`; `CapacityLayer(kl=KnowledgeLayer)` constructor param wires
the dependency once at construction (conditional injection — only fires
when `self._kl is not None` per R5 PB-B). Bodies missing `kl` raise
`RuntimeError` (R3 PB-F; programmer error).

`Graph.add_node` signature reconciliation (R4 §am-impl-1): L1 takes
`type_name` not `type_`; `write_and_validate` keeps L2-convention
`type_` on the handle method and translates at the L1 boundary.

NodeType locks (R4 §am-impl-3): `"Memory"` (Phase 13 `build_memories_
schema`) and `"ProblemTraceEntry"` (Phase 13 `build_problem_trace_
schema`) — NOT the ADR §Skeleton's speculative `"ConsolidatedMemory"`.

## §amendment-2 — Phase 34 OCC defer + clause-3 partial-close (halvim, 2026-05-26)

Two narrow Phase 34 documentary clauses (R1 PB-G + R2 PB-A):

**Clause 1 — OCC retry deferred until L1 grows OCC contract.** The
§Decision failure-mode table lists `OCC_RETRIED_OUT` with capacity-side
retry up to N. L1's `add_node` is not OCC-checked at Phase 34 — the
`_version: int` ADR-0127 field exists on Node + Composite but no
`OCCMismatchError` raise site exists. Phase 34 defers writing retry
code as speculative. `WriteResult.extras` reserves the `"retry_count"`
key for future use (convention; not enforced). Retry semantics get
pinned when L1 grows the OCC contract.

**Clause 2 — Clause 3 partial close (mint-key surfacing only).** Phase
34 R2 PB-A: DataState shapes for `consolidate:mm` and `trace:problem`
tighten from opaque to `ShapeDescriptor.record(...)` with the MINIMUM
fields capacity bodies need to read for `mint_iri`. L4-flow tightening
of the rest of the record shape (e.g., `CompositeInstance` field
binding for consolidate) stays deferred per §amendment-1 clause 3 + ADR-0147
per-flow build discipline.

## §amendment-3 — Phase 39 multi-NodeType dispatch — tuple-key registry + mint_iri signature (halvim, 2026-06-XX)

Phase 39's `memories` → `episodic_memories` rename (ADR-0044
§amendment-3 + ADR-0150 §amendment-4) hosts two NodeTypes (`Episode` +
`Memory`) under a single role. The Phase 33/34 single-minter
`_IRI_BUILDERS` registry shape (`Dict[role, minter]`) cannot dispatch
two minters under one role.

**Amended surface:**

* `_IRI_BUILDERS: dict[tuple[str, str], Callable]` keyed
  `(role, NodeType_name)`. Three entries post-rename:
  - `(ROLE_EPISODIC_MEMORIES, "Episode") → _mint_episode`
  - `(ROLE_EPISODIC_MEMORIES, "Memory") → _mint_memory_composite`
  - `(ROLE_PROBLEM_TRACE, "ProblemTraceEntry") → _mint_problem_trace`
* `KLWriteHandle.mint_iri(self, type_: str, **content: Any) -> str` —
  signature change from Phase 33/34's `mint_iri(self, **content)`.
  Lookup body: `_IRI_BUILDERS[(self.role, type_)]`. Caller flow
  unchanged via `write_and_validate(type_=..., **content)` forwarding.
* `KeyError` message updated to surface both role and NodeType when no
  minter registered for the `(role, type_)` pair.

**Out-of-scope for amendment-3:**

* Per-flow build discipline (§amendment-1 clauses 4 + 5; ADR-0147) —
  unchanged. Registry-shape change is orthogonal to per-flow build.
* `KLWriteHandle.write_and_validate` signature — unchanged; passes
  `type_` through.
* ADR-0143 `KLWriteHandle` Surface + Constraint — unchanged;
  cross-reference added at ADR-0143 `## Implementation references`
  for traceability only (no §amendment on ADR-0143).

**Rationale:** Single-minter-per-role was a Phase 33 simplification
that held while every shipped role mapped to a single NodeType. D-L2-17
+ Chat B D-B48 break the 1:1; tuple-key future-proofs further
multi-NodeType roles (Phase 43 schema-v2 will register Memory
composite contents + the `memory_contains_episode` IntergraphEdge).
Single-dispatcher-with-kind-kwarg (option (b) at design pass) rejected:
less explicit dispatch failure mode + harder to validate per-NodeType
minter signatures.

See `confirmation_docs/PHASE_39_DESIGN_LOG.md` R1 PB-N1 / PB-N3 / PB-N4
for design pass closure and dispatch-shape alternatives considered.

## §Amendment (Phase 42 — ADR-0159)

The symmetric write invocation contract is unchanged; only the access path becomes typed (`context.kl` via `KLHandle`). Body migration deferred to Phase 46 (PB-23).

## §Amendment (Phase 48 — write handle from `context.writeable`; ADR-0180)

The symmetric validate-then-write contract remains **unchanged** — the L3 body still validates then writes through a `KLWriteHandle`. What changes is **how the body obtains the handle**: instead of `kl.writeable(session, role, scope, version)` (which required a Session object on the body), the body calls **`context.writeable(role, scope, version)`** — a pre-authorized, session-bound capability that L4 `dispatch.py` injects onto `CapacityContext` and gates at call-time (scope-aware) per ADR-0180. L3 is still the write surface; it no longer holds a principal. `consolidate`/`trace` migrate at Phase 48; PB-23 closes. See ADR-0180.
