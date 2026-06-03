---
title: KLWriteHandle pattern for L3 write capacities
status: Accepted
date: 2026-04-27
layer: L2
---

# ADR-0143: `KLWriteHandle` pattern for L3 write capacities

**Status:** Accepted (flipped Proposed → Accepted at Phase 34, 2026-05-26;
halvim; see §Implementation (Phase 34) footer)

**Date:** 2026-04-27

**Related:** ADR-0138 (KL drops write API), ADR-0139 (hybrid invariant home), ADR-0142 (XRef cutover).

## Context

ADR-0138 deletes KL's write API. ADR-0139 puts semantic invariants in KL validators that L3 write capacities call. L3 capacities still need a way to:

(i) find the right metagraph + role-graph for a session + role,
(ii) mint an IRI per the role's pattern,
(iii) call validators before mutating,
(iv) call L1 mutation primitives on the right graph.

KL has no write API. But raw `MetagraphView` + free-floating helpers force every capacity to repeat (i)–(iii) inline. The shared addressing logic needs *somewhere*.

## Decision

**KL exposes a lightweight typed handle: `kl.writeable(session, role, scope='local'|'global') -> KLWriteHandle`.**

The handle is a non-mutating accessor. It encapsulates the routing and validators an L3 capacity needs to perform a write. It does not call L1 mutation primitives itself — the capacity does, using the L1 `Graph` reference the handle returns.

### Surface

```python
class KLWriteHandle:
    role: RoleName               # e.g. "memories", "concepts"
    scope: Literal['local', 'global']
    session: SessionProtocol     # for capability re-checks at handle methods

    def graph(self) -> Graph:
        """Returns the L1 graph for the active version of `role` in the session's metagraph.
        Capacity calls graph().add_node(...), graph().add_xref(...), etc. for mutation."""
        ...

    def metagraph(self) -> Metagraph:
        """Returns the parent metagraph (Global or session's Local). For XRef target lookup."""
        ...

    def mint_iri(self, **content) -> str:
        """Mints an IRI per the role's IRI builder. content kwargs feed the builder."""
        ...

    def validate_node(self, value, type_, **refs) -> ValidationResult:
        """Composes role-appropriate validators. Returns ValidationResult."""
        ...

    def validate_xref(self, target_metagraph: Metagraph, target_role: RoleName,
                      target_id: str, ref_type: str) -> ValidationResult:
        """Validates cross-metagraph ref: target exists in active version of target_role."""
        ...
```

### Usage skeleton

```python
def capacity_consolidate_memory(session, mm: CompositeInstance) -> WriteResult:
    handle = kl.writeable(session, role=ROLE_MEMORIES, scope='local')
    iri = handle.mint_iri(user_id=session.user_id, memory_id=mm.root_id)
    if not (r := handle.validate_node(value=mm.summary, type_="ConsolidatedMemory")).ok:
        return ProblemTraceRecord(violation=r)
    handle.graph().add_node(node_id=iri, value=mm.summary, type_="ConsolidatedMemory")
    handle.graph().add_xref(source_id=iri,
                            target_metagraph_id=handle.metagraph().metagraph_id,
                            target_role="task-patterns",
                            target_id=mm.task_pattern_iri,
                            ref_type="DERIVED_FROM")
    return WriteResult(iri=iri)
```

### Constraint

**The handle never mutates.** No `add_node`, no `add_xref`, no `set_property`. The capacity always reaches mutation through `handle.graph()` and calls L1 directly.

This is the social contract that prevents `KLWriteHandle` from accreting into a write API. Code review enforces it.

## Rationale

Three options were on the table:

- **A. Raw L1 graph references** (`kl.get_writeable_graph(...)` + `kl.iri_for(...)` + `kl.validators.*`): minimal surface, but every capacity reimplements routing + validator composition.
- **B. `KLWriteHandle`** (this ADR): captures routing + validator composition once; capacity code is shorter and less prone to skipping a step.
- **C. Capacity-side helpers in `mindsos_capacity/kl_write_helpers.py`**: shared boilerplate, but utility code outside KL that knows KL internals.

B is the smallest *useful* surface. A's per-capacity boilerplate is real cost. C splits ownership wrong — code that depends on KL's role-graph routing belongs at KL.

The risk in B is accretion: methods get added that do half the mutation. The handle's "never mutates" rule is the explicit guard. Code review enforces it. If the rule erodes, this ADR gets superseded.

## Consequences

**Good:**

- L3 write capacities are short and consistent. Routing + validator composition lives once.
- KL remains write-API-free in the strict sense (the handle exposes accessors and validators, not mutation methods).
- Adding a new role-graph requires adding an IRI builder + validators in KL; capacities pick up the new role automatically through `kl.writeable(session, role=...)`.

**Tradeoffs:**

- One more KL surface to learn (`KLWriteHandle`).
- The "never mutates" rule is social, not enforced by types alone. A `KLWriteHandle.add_node()` method would be a regression that type-checking won't catch.
- Capability re-checks happen on handle methods (e.g. `mint_iri` could check `CAN_WRITE_LOCAL` for the role). Two cap-check sites: capacity entry + handle methods. Defence-in-depth or duplication, depending on framing.

## Alternatives considered

1. **A — Raw L1 + helpers.** Rejected as primary; per-capacity boilerplate.
2. **C — Capacity-side helpers.** Rejected; ownership split.
3. **`KLWriteContext` as a context manager** (`with kl.writeable(...) as ctx: ...`). Considered; adds lifecycle (enter/exit) for nothing — the handle is stateless. Held; reopen if write capacities grow transactional semantics.
4. **Separate read and write handles for symmetry.** Rejected — `MetagraphView` already covers reads (ADR-0138 §retains).

## Implementation references

- New module: `mindsos_knowledge/write_handle.py` — `KLWriteHandle` dataclass + methods.
- New entry point: `KnowledgeLayer.writeable(session, role, scope)`.
- Validator composition: handle methods compose `mindsos_knowledge/validators.py` functions per role.
- `docs/dev/internals/knowledge.md` documents the "never mutates" rule.
- ADR moves to Accepted when (a) `KLWriteHandle` ships, (b) at least two L3 write capacities use it, (c) the "never mutates" rule is in the code review checklist (`docs/dev/review-checklist.md`).
- ADR-0146 §amendment-3 (Phase 39 ship — 2026-06-XX) — `KLWriteHandle.mint_iri` signature evolved to `mint_iri(self, type_: str, **content) -> str` and `_IRI_BUILDERS` registry shape evolved to `(role, NodeType_name) → minter` tuple-key. Handle pattern + Surface + Constraint defined in this ADR are unchanged; signature evolution is a registry-dispatch change, not a handle-pattern change.

## §Implementation (Phase 33 — stub-only; halvim, 2026-05-26)

Phase 33 ships the module + entry-point SURFACE; the handle bodies are
partially stubbed per ADR-0146 §amendment-1 clause 5:

- `mindsos_knowledge/write_handle.py` NEW — frozen-dataclass
  `KLWriteHandle(role, scope, session, _kl, _metagraph)`.
- `KnowledgeLayer.writeable(session, role, scope) -> KLWriteHandle`
  NEW method; routes `scope='local'` to `session.user_id`'s Local,
  `scope='global'` to Global. Raises `ValueError` on `scope='local'`
  with `session=None` (ADR-0080 carve-out doesn't extend to Local).
- `metagraph()` returns the real L1 Metagraph (read-only state
  inspection; safe at stub phase).
- `graph()` + `mint_iri()` + `validate_node()` + `validate_xref()`
  raise `WriteHandleNotWiredError`. Phase 34 (ADR-0146) wires
  `graph()` + `mint_iri()`; Phase 36 (ADR-0139) wires the validators.

Phase 33 satisfies §Accept criterion (a) PARTIALLY (handle ships as
stub) and (b) PARTIALLY (`capacity:consolidate:mm` +
`capacity:trace:problem` both call `writeable()` + `graph()`, surfacing
`WriteHandleNotWiredError` through the envelope). §Accept criterion (c)
(`docs/dev/review-checklist.md` with "never mutates" rule) stays
unsatisfied → **ADR-0143 status remains Proposed.** Phase 34 ships the
working body + the review-checklist entry → ADR-0143 flips Accepted at
Phase 34.

ADR-0143 §Constraint ("never mutates") is honoured at Phase 33 by the
handle's frozen-dataclass shape + the fact that `graph()` raises before
any mutation surface is exposed. Phase 34's body must NOT add mutation
methods (`add_node` etc.); capacity code reaches mutation through
`handle.graph()` and calls L1 directly.

## §Implementation (Phase 34 — Accepted; halvim, 2026-05-26)

Phase 34 wires the handle body and ships the review checklist, closing
all three §Accept criteria. **Status flips Proposed → Accepted.**

- §Accept criterion (a) — `KLWriteHandle` ships with working
  `graph()` + `mint_iri()` + `write_and_validate()` bodies; the
  module + entry point are no longer stub-only.
- §Accept criterion (b) — `capacity:consolidate:mm` +
  `capacity:trace:problem` (the two write capacities shipped at
  Phase 33) call `handle.write_and_validate(...)` on their success
  path, returning `WriteResult` per ADR-0146 §Decision.
- §Accept criterion (c) — `halvim_mindsos/docs/dev/review-checklist.md`
  ships with the "KLWriteHandle never mutates" rule (item 1) plus 2
  recurring rules surfaced at Phase 34 (outputs=() write-terminator;
  capacity-body context-routing for `session` + `kl`).

The handle gains one new field (`_version: str`, required at the end
of the frozen dataclass) so :meth:`mint_iri` knows which version
literal to embed in the produced IRI; the version threads through
`KnowledgeLayer.writeable(session, role, scope, *, version="v1")` at
the entry point (default `"v1"` is the sole shipped version under
current role schemas).

`graph()` body iterates `self._metagraph.graphs.values()` and returns
the L1 `Graph` whose `.role` matches `self.role`; raises `KeyError`
on absent role (programmer error per ADR-0146 §Decision).

`mint_iri(**content)` dispatches via a minimal 2-entry registry
(`_IRI_BUILDERS` in `mindsos_knowledge/identifiers.py`) keyed by role.
Per-flow build discipline (ADR-0147) — only the 2 shipped write
capacities have registry entries; Phase 35+ adds entries alongside
new write capacities. Missing required content kwargs surface as
`KeyError` per ADR-0146 §Decision.

`write_and_validate(*, value, type_, **mint_content) -> WriteResult`
composes `mint_iri → graph().add_node(value=value, type_name=type_,
node_id=iri) → WriteResult`. Phase 34 scope is L1-structural
validation only; L2 semantic validators (`validate_node` /
`validate_xref`) remain stubbed and integrate at Phase 36 (ADR-0139).

The `type_` kwarg is the L2-convention name; the body translates to
L1's `type_name` kwarg at the `add_node` boundary (R4 §am-impl-1
reconciliation against `Graph.add_node` signature `(value, type_name,
*, properties=None, node_id=None)`).

ADR-0143 §Constraint enforcement: the review checklist (§Accept (c))
is the social-enforcement mechanism; future PRs that try to add
`KLWriteHandle.add_node`, `.add_xref`, etc. should be rejected on
review per item 1 of the checklist.

## §Implementation (Phase 36 — validate_node body wired; validate_xref defers per-flow; halvim, 2026-05-27)

ADR-0143's `validate_node` body was stubbed at Phase 34 (raised
`WriteHandleNotWiredError`); Phase 36 (ADR-0139 §amendment-1)
wires it. The body dispatches via a per-role adapter registry
(`_VALIDATORS_BY_ROLE` in `mindsos_knowledge.validators`) that
mirrors `_IRI_BUILDERS`' shape per R3-PB-A. Adapter for the
handle's `self.role` runs the role-appropriate validator chain
and returns a `ValidationResult` (frozen dataclass with
`ok: bool` + `violation: Optional[str]`; v1 minimal per
Phase 36 R2-PB-D). Phase 36 ships 2 adapter entries
(`memories` + `problem-trace`); roles without a registered
adapter raise `WriteHandleNotWiredError` (per-flow extension per
ADR-0139 §amendment-1 clause 3).

`validate_xref` STAYS raising `WriteHandleNotWiredError` —
defers per-flow alongside the first XRef-writing L3 capacity. The
underlying validators (`validate_local_to_global_ref`,
`validate_ref_type`) ship at Phase 36 as pure functions and may
be called directly from a capacity body per ADR-0139
§Capacity-contract fallback.

`write_and_validate` itself remains unchanged from Phase 34 —
composition lives in the capacity body precondition immediately
preceding the call (ADR-0139 §Decision §Capacity-contract). The
handle stays narrow per §Constraint; the new convenience composite
(`validate_node`) is read-only by construction (returns
`ValidationResult`; no mutation; no I/O).

§Constraint enforcement (review-checklist.md): Phase 36 splits
item 1's `validate_node` / `validate_xref` bullet to reflect
the partial wiring + adds a new section 4 "Capacity preconditions
call semantic validators (ADR-0139)" enforcing that capacity
bodies call the composite (or compose validators directly) before
`write_and_validate`. Bypass = code-review failure per ADR-0139
§Decision.
