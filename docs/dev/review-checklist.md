---
last_confirmed_phase: 36
verified_at: unverified
---

# Code review checklist

Phase 34 ship (R1 PB-D). Closes ADR-0143 §Accept criterion (c) — the
"never mutates" rule on `KLWriteHandle` lives here.

Three items. Future phases append.

## 1. `KLWriteHandle` never mutates (ADR-0143 §Constraint)

The handle exposes accessors + validators only:

* `metagraph()` — read-only state inspection.
* `graph()` — returns the L1 `Graph` reference; mutation happens via
  `graph().add_node(...)` on the L1 surface, not on the handle.
* `mint_iri(...)` — pure IRI construction.
* `validate_node(...)` — wires at Phase 36 via `_VALIDATORS_BY_ROLE`
  adapter; returns `ValidationResult` composite. Pure (no mutation).
* `validate_xref(...)` — defers; wires alongside first XRef-writing
  capacity per per-flow discipline (ADR-0139 §amendment-1 clause 3
  carry-forward).
* `write_and_validate(...)` — composite that calls `graph().add_node`
  through L1; the handle still does not own a mutation method.

**Reject** any PR that adds `KLWriteHandle.add_node`, `.add_xref`,
`.set_property`, or any method that calls a L1 mutation primitive
through `self.*` instead of `self.graph().*`. Capacity bodies that need
mutation reach for `handle.graph()` and call L1 directly, or use
`handle.write_and_validate(...)` which encapsulates the L1 call site.

The handle is a `@dataclass(frozen=True)` — that prevents field
mutation but does NOT prevent method accretion. The discipline is
social; this checklist is the enforcement.

## 2. A write capacity DECLARES itself — `writes=True`

⚠ **SUPERSEDED IN PART, 2026-09-18 — `mindsos_llm` plan ruling R7**
(ADR-0146 §amendment-4, ADR-0180 §amendment-4). The text below is kept
because the reject rule it states was followed for a year and a reviewer
who remembers it needs to see what replaced it.

> **SUPERSEDED:** *"Write capacities have `outputs=()` (pipeline
> terminators) … **Reject** any PR that registers a write capacity with
> non-empty `outputs=(...)`."*

`outputs == ()` says *produces no DataState*. It never said *writes*, and
the two are orthogonal — they coincided only because every write capacity
that shipped before R7 happened to be a terminator. ADR-0210 §amendment-4
rules a recorder that writes AND declares its pointer as an output, so
that a run graph names what was written.

**The rule now:**

* A capacity that mutates L2 declares **`writes=True`**. That declaration,
  not the output count, is what puts `context.writeable` on its context —
  at `capacity_layer.invoke` and at `L4Dispatcher.build_context` alike.
* A write **MAY** declare outputs. A write with none is a *terminator*:
  `runtime.invoke` bypasses output validation and surfaces the
  `WriteResult` via `InvocationResult.write_outcome`. A write WITH a
  declared output returns it in `.outputs` like any other capacity, and
  `write_outcome` stays `None`.
* Phase 30's BFS pipeline finder still treats a terminator as a dead-end.

**Reject** any PR that reaches `context.writeable` from a body whose
declaration does not say `writes=True`, or that declares `writes=True`
in a module no body of which writes. Both directions are gate-enforced by
`tests/architecture/test_write_is_declared.py`; the checklist is the
explanation, the guard is the enforcement.

## 3. Capacity bodies extract `session` + `kl` via `context.get(...)`

Per ADR-0146 §amendment-1 clause 2 (Phase 33) + Phase 34 R0 PB-5. The
capacity callable signature is `(**inputs, context=context)`; `session`
and `kl` (when present) live in `context`, not as positional args.

**Reject** any PR that:

* Adds positional `session` or `kl` params to capacity body signatures
  (`def my_capacity_impl(session, kl, **inputs): ...`).
* Routes `session` or `kl` through `**inputs` instead of `context`.
* Constructs a fresh `KnowledgeLayer` inside the body
  (`kl = KnowledgeLayer.bootstrap()`) instead of reading from context.

The CapacityLayer constructor (`CapacityLayer(kl=...)`) is the
single-source-of-truth wiring; `invoke()` injects into context
conditionally; bodies extract via `context.get("kl")` and raise
`RuntimeError` if missing (programmer error per ADR-0146 §Decision).

## 4. Capacity preconditions call semantic validators (ADR-0139)

Per ADR-0139 §Decision §Capacity-contract. L3 write capacities call
the semantic validators required by the capacity's role as
preconditions, before invoking `handle.write_and_validate(...)`.

**Prefer** `handle.validate_node(value=..., type_=...)` composite when
the role has a registered adapter in `_VALIDATORS_BY_ROLE` (Phase 36: `episodic_memories` + `problem-trace`; `memories` renamed Phase 39). The composite owns metagraph routing
internally and keeps the role→chain mapping in one place.

**Fallback** — direct `validate_*` calls from
`mindsos_knowledge.validators` remain valid (ADR-0139
§Capacity-contract) for one-off checks or roles without a
registered composite.

Body shape (R2-PB-J):

```python
vr = handle.validate_node(value=..., type_="Memory")
if not vr.ok:
    raise SemanticValidationError(vr)
return handle.write_and_validate(...)
```

**Reject** any write-capacity PR that:

* Calls `handle.write_and_validate(...)` (or
  `handle.graph().add_node(...)`) without a preceding semantic-
  validator check for the role's required invariants.
* Catches `SemanticValidationError` inside the capacity body to
  swallow it — failure must surface to the runtime envelope per
  ADR-0072 + ADR-0146 §amendment-1 clause 1 (raise-not-PTR posture
  preserved at Phase 36; L4 consumer drives eventual clause-1
  flip).
* Adds a new write capacity targeting a role that lacks an
  adapter entry in `_VALIDATORS_BY_ROLE` without simultaneously
  adding the adapter (per-flow extension per ADR-0139
  §amendment-1 clause 3).

The bypass discipline is social; this checklist is the
enforcement (ADR-0139 §Decision: "L3 capacities that skip
validators are a code-review failure, not a runtime error").
