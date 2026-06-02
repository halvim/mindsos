---
title: Hybrid invariant home — L1 structural, KL semantic
status: Accepted
date: 2026-04-27
layer: L2
---

# ADR-0139: Hybrid invariant home — L1 structural, KL semantic

**Status:** Accepted (flipped Proposed → Accepted at Phase 36 ship per
§amendment-1; halvim, 2026-05-27)

**Date:** 2026-04-27

**Related:** ADR-0138 (KL drops write API), ADR-0143 (`KLWriteHandle`), ADR-0123 (indexes + `verify_integrity`), ADR-0128 (hybrid XRef), ADR-0133 (soft-delete properties).

## Context

ADR-0138 deletes KL's write API. The invariants that KL writes used to enforce inline (Local→Global ref points to active version-graph; alignment role naming canonical; role-graph routing rules) need a new home.

Two extreme options: push every invariant into L1 schema, or duplicate them inside each L3 capacity. Both are wrong — the first overloads L1 schema with semantic rules it has no shape to express; the second guarantees drift across capacities.

## Decision

**Hybrid: L1 enforces structural invariants at write; KL exposes pure-function semantic validators that L3 capacities call as preconditions.**

### Structural invariants — L1's responsibility

L1 enforces these unconditionally at write time, raising on violation:

- XRef integrity: target metagraph + target id exists at write time when target is in scope (ADR-0128).
- Schema shape: node/edge labels, required properties, edge cardinality (existing schema validation).
- Reserved property keys: `_version`, `deprecated_at`, `disputed_at`, `kl:*`, `server:*`, `ref:*`, `ov__*` (per ADR-0130 + ADR-0133).
- ID uniqueness: indexed at FalkorDB level; persist-time double-check (ADR-0123).

Violations raise specific exceptions (`XRefIntegrityError`, `SchemaViolationError`, `ReservedKeyError`, `DuplicateIdError`). Capacities that hit these are buggy — the exceptions surface that.

### Semantic invariants — KL's responsibility

KL exposes pure-function validators in `mindsos_knowledge/validators.py` (or equivalent module). Each validator returns `ValidationResult` (success or structured violation); no validator mutates. L3 write capacities call them in preconditions before any L1 mutation.

Initial validator set (covers the invariants today's `add_local_node` / `add_local_edge` / `add_local_alignment` / `promote` enforce):

- `validate_local_to_global_ref(target_role, target_iri, mg) -> ValidationResult` — target IRI exists in active version-graph of `target_role` in Global.
- `validate_role_routing(role, scope, mg) -> ValidationResult` — `role` is a registered role-graph in the scope's metagraph.
- `validate_alignment_role_naming(role) -> ValidationResult` — canonical `alignment:<a><->b>` with sorted roles.
- `validate_ref_type(ref_type, target_role) -> ValidationResult` — `ref_type` ∈ `REF_TYPES`; allowed for the target role.
- `validate_promotion_candidate(local_iri, mg) -> ValidationResult` — candidate is a Local draft, not already promoted, not already deprecated.

Validators are idempotent and side-effect-free. Capacity authors compose them; failure modes return a `ProblemTraceRecord` from the capacity (per ADR-0146), not a raise.

### Capacity contract

Every L3 write capacity follows this skeleton:

```python
def capacity_consolidate_memory(session, mm: CompositeInstance) -> WriteResult:
    handle = kl.writeable(session, role=ROLE_MEMORIES, scope='local')
    # 1. Validate (KL semantic invariants)
    for validator in [validate_role_routing, ...]:
        result = validator(...)
        if not result.ok:
            return ProblemTraceRecord(violation=result)
    # 2. Mutate (L1 primitives via handle)
    new_iri = handle.mint_iri(...)
    handle.graph().add_node(...)  # L1 enforces structural invariants
    handle.graph().add_xref(...)
    return WriteResult(iri=new_iri)
```

L3 capacities that skip validators are a code-review failure, not a runtime error. Bypassing is technically possible (capacities have raw L1 access via the handle); the convention is enforced socially.

## Rationale

L1 schema is the right place for structural invariants because:

- They're the same across all consumers.
- They're cheap to express (already do shape + uniqueness).
- Violations are unrecoverable from the consumer's side anyway.

KL is the right place for semantic invariants because:

- They depend on KL's data (active version-graph, role-graph registry, alignment naming).
- They're testable as pure functions without mocking L1 or sessions.
- They're discoverable: `mindsos_knowledge/validators.py` is the index of "what L2 cares about beyond shape."

L3 capacities are the wrong place because they multiply by capacity count and drift on every change.

## Consequences

**Good:**

- Three layers each own a coherent slice of the invariant surface.
- Validators are unit-testable in isolation.
- New invariants get one home (KL) and propagate to all capacities by code review.
- L1 schema doesn't bloat into a semantic-rule language.

**Tradeoffs:**

- Validator-bypass is technically possible; relies on convention.
- Adding a new validator requires a code-review rule that capacity authors call it.
- Migrating existing KL write-method invariants to validators is mechanical but not free (~200–300 LOC moves).

## Alternatives considered

1. **All invariants into L1 schema.** Rejected — schema language would have to grow to express "ref points to active version-graph"; that's not schema, that's runtime semantic.
2. **All invariants embedded in each L3 capacity.** Rejected — duplication and drift across N capacities; a single invariant change touches N places.
3. **Validators on L3 capacities (each capacity exports its preconditions for shared use).** Rejected — validators that depend on KL data should live with KL data; this option scatters them by accident.

## Implementation references

- New module: `mindsos_knowledge/validators.py`.
- `KLWriteHandle.validate_*` shorthands (ADR-0143) call into this module.
- ADR moves to Accepted when (a) all listed validators ship as pure functions, (b) at least one L3 write capacity in code uses the pattern, (c) `docs/dev/internals/knowledge.md` documents the validator surface.

## §amendment-1 (Phase 36 ship; halvim, 2026-05-27 — flip Proposed → Accepted)

ADR-0139 Status flipped Proposed → Accepted at Phase 36. Three clauses
close the §Acceptance gate and lock the carry-forward shape for future
per-flow validator additions.

**Clause 1 — §Acceptance criterion (a) satisfied literally (NOT relaxed).**
All 5 listed validators ship as pure functions in
`mindsos_knowledge/validators.py` per R2-PB-A. Per-flow discipline
(ADR-0147 §amendment-1 clause 3) governs *L3 capacity contract
surfaces*; validators are L2 substrate pure functions with
ADR-frozen signatures and no consumer-defined fields — per-flow does
not gate them at the function level. The literal closure preserves
ADR hygiene (no §Accept text edits) and matches Phase 35's "clarify,
don't rewrite" precedent (ADR-0147 §amendment-1 R2-PB-β).

**Clause 2 — §Acceptance criterion (b) satisfied via wired capacities.**
Both shipped L3 write capacities (`capacity:consolidate:mm` +
`capacity:trace:problem`) call `validate_role_routing` via
`handle.validate_node(...)` as a precondition before
`handle.write_and_validate(...)` per §Decision §Capacity-contract.
Pre-mint timing per R3-PB-H — semantic validator fires before IRI
mint and L1 add_node, giving earlier diagnostics than
`handle.graph()`'s `KeyError` would surface.

**Clause 3 — Per-flow extension for adapter registry going forward.**
`_VALIDATORS_BY_ROLE` (the `KLWriteHandle.validate_node` dispatch
registry, mirroring `_IRI_BUILDERS` shape per R3-PB-A) ships at
Phase 36 with **exactly 2 adapter entries** (`memories` +
`problem-trace`). New adapters land alongside their consuming L3
write capacity per the per-flow discipline locked at ADR-0147
§amendment-1 clause 3. Roles without a registered adapter raise
`WriteHandleNotWiredError` from `validate_node`. The
`handle.validate_xref` composite STAYS unwired at Phase 36 —
defers per-flow alongside the first XRef-writing capacity. The
underlying validators (`validate_local_to_global_ref`,
`validate_ref_type`) ship as pure functions and may be called
directly from a capacity body per §Capacity-contract fallback.

## §Implementation (Phase 36 — Accepted; halvim, 2026-05-27)

ADR-0139 Status flipped Proposed → Accepted at Phase 36.
§amendment-1 clauses 1–3 close §Acceptance criteria (a) (b) (c).

**Wiring shape (R0 PB-1 = B; R2-PB-H + R3-PB-A):**

- Semantic validators are composed in **capacity bodies** as
  preconditions, not inside `write_and_validate`. The handle stays
  narrow per ADR-0143 §Constraint.
- `KLWriteHandle.validate_node(value, type_, **refs)` is the
  canonical convenience composite — dispatches via
  `_VALIDATORS_BY_ROLE` (per-role adapter registry mirroring
  `_IRI_BUILDERS`). Phase 36 ships 2 adapters with single-validator
  chains (`(validate_role_routing,)` for both `memories` and
  `problem-trace`).
- Direct validator calls from `mindsos_knowledge.validators` remain
  valid per §Capacity-contract fallback (one-off checks or roles
  without a composite). The convenience composite is preferred when
  available; `docs/dev/internals/knowledge.md` §Validator surface
  documents both styles.

**Failure semantics (Phase 34 raise-not-PTR posture preserved per
R5-PB-D).** Capacity bodies raise `SemanticValidationError`
(carrying the failed `ValidationResult` on `.result`) on
`not result.ok`. The runtime envelope catches per ADR-0072 and
surfaces as `InvocationResult(success=False, error=<exc>)`.
ADR-0146 §amendment-1 clause 1 (raise vs return PTR) remains open
— the L4 consumer drives the eventual flip. The `.result`
attribute on `SemanticValidationError` is the carry-forward hook
for that closure: a future PTR-returning capacity body builds a
`ProblemTraceRecord` from `exc.result` without re-running the
validator.

**Cross-phase note:** Phase 36 does NOT re-open ADR-0143 §Decision
or ADR-0146; both remain Accepted. ADR-0143 §Implementation
Phase 36 footer documents the `validate_node` body wire + the
`validate_xref` defer per-flow. ADR-0147 §amendment-1 clause 3
remains binding for new L3 write capacities; this ADR's clause 3
(adapter per-flow extension) is the L2-side parallel.
