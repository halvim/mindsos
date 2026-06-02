---
title: Soft-delete via deprecated_at / disputed_at properties; default include_deprecated=False
status: Accepted
date: 2026-04-27
layer: L1
amends: [0032]
---

# ADR-0133: Soft-delete via `deprecated_at` / `disputed_at` properties; default `include_deprecated=False`

**Status:** Accepted (Phase 10 — 2026-05-16; substrate + iterator/loader filter shipped together per P68 merge)

**Date:** 2026-04-27

**Amends:** ADR-0032 (reserved property keys — extended with `deprecated_at`, `disputed_at`).

**Related:** ADR-0116 [Reserved] (Edge soft-delete model — pivot ADR; this ADR provides the *representation*; 0116 covers the *model* of when/how to deprecate). PIVOT §6.B.6 (default query semantics).

## Context

The pivot's release model uses soft-delete as the default correction mechanism (PIVOT §3 item 6, §6.B.6). Edges can be marked `deprecated` (admin retired) or `disputed` (admin disagrees but not yet retired). Default reads skip soft-deleted edges; opt-in flag re-includes them.

Three implementation questions sat unanswered:

1. **How is "deprecated" represented at the data level?** Property on edge? Edge label suffix? Tombstone-anchored marker? Core-unaware (KL-only)?
2. **Which Core read APIs honor the default filter?** `Graph.iter_edges`? `Metagraph.iter_*`? Loader?
3. **Is the filter a Core concern or KL concern?** If Core-unaware, L3 capacity-state queries hitting Core directly still see deprecated edges; pivot's "every layer defaults to include_deprecated=False" doesn't hold uniformly.

The L1 redesign session resolved these (M9 + N1).

## Decision

### Representation: property-on-edge

Two new edge properties:

- `deprecated_at: datetime | None` — when this edge was deprecated. `None` = active.
- `disputed_at: datetime | None` — when this edge was marked disputed. `None` = not disputed. `disputed_at` and `deprecated_at` can both be set; deprecated subsumes disputed for filtering.

Both join `RESERVED_PROPERTY_KEYS` (per ADR-0032). User properties cannot use these names.

**Reversibility:**

- Undeprecate: `SET e.deprecated_at = NULL`. Property update; cheap.
- Undispute: `SET e.disputed_at = NULL`. Same.

Soft-delete is an attribute, not a separate edge. The same edge_id stays the same edge across the deprecate/undeprecate cycle.

### Default read filter: `include_deprecated=False` on Core read APIs

Every Core iterator and getter that returns edges gains:

```python
include_deprecated: bool = False
```

Affected methods:

- `Graph.iter_edges(include_deprecated=False)`
- `Graph.get_edges_for_node(include_deprecated=False)`
- `Graph.iter_hyperedges(include_deprecated=False)` — hyperedges treated symmetrically
- `Metagraph.iter_metaedges(include_deprecated=False)`
- `Metagraph.iter_metahyperedges(include_deprecated=False)`
- `GraphLoader.load(...)` — passes through to subsequent reads via the loaded Graph's iterator defaults
- `Metagraph.iter_xrefs(include_deprecated=False)` — XRefs (per ADR-0128) honor the same filter

**Filter semantics:**

```cypher
// include_deprecated=False (default):
WHERE e.deprecated_at IS NULL
// include_deprecated=True:
// (no filter)
```

`disputed_at` does **NOT** filter by default. Disputed edges are still visible — disputed = "this is wrong but the data is still here for now," whereas deprecated = "stop showing this." Users can construct their own filters on `disputed_at` if they want to hide disputed too.

### Edges only; nodes are not soft-deletable

In v1 scope (PIVOT §3 item 6), only edges support soft-delete. Nodes have hard-delete (existing tombstone mechanism, ADR-0024) or no-delete. Atom-delete via refcount is v2 (PIVOT §2 row 6c).

This means: if a Global node is "wrong," the admin marks the edges connecting it as `deprecated_at`. The node itself stays. v2's atom-delete handles the case where the node should genuinely vanish.

### Hyperedges and metaedges

`HyperEdge` and `MetaEdge` and `MetaHyperEdge` all gain the same two reserved properties and honor the same default filter. Symmetric with edges.

### Coordinated changes for compositional metaedges

`CompositionalMetaEdge` (per ADR-0117 [Reserved]) is **write-once**: composition is identity. Compositional metaedges therefore cannot be deprecated either. The data model: `CompositionalMetaEdge` rejects writes to `deprecated_at` and `disputed_at` with `CompositionalImmutableError`.

### KL and pivot integration

KL's `MetagraphView` reads pass through Core's `include_deprecated` parameter. KL deprecation API (forthcoming, owned by ADR-0116) sets `deprecated_at` and `disputed_at` on edges through the KL write path; the underlying Core update is `SET e.deprecated_at = $now`.

The pivot's audit gate (ADR-0115 [Reserved]) queries deprecated-since-last-release as part of `ImpactReport.summary.deprecated_edge_count`.

### Loader behavior

`GraphLoader.load(include_deprecated=False)` filters at the Cypher level — deprecated edges are never materialised in the in-memory `Graph` object. Callers that need the full set (audit gate, repair tools) pass `include_deprecated=True`. The loader doesn't carry the filter as state on the loaded `Graph` — subsequent calls to `Graph.iter_edges` re-apply the default at iteration time.

Consequence: loading a Graph with `include_deprecated=False` and then iterating with `include_deprecated=True` returns nothing extra (the deprecated edges weren't loaded). Documented as a gotcha.

## Rationale

Property-on-edge wins over the alternatives because:

- It's the cheapest representation. No new Cypher concepts; just two more properties.
- Reversibility is a property update, not a delete-then-recreate.
- The filter compiles to a simple Cypher `WHERE e.deprecated_at IS NULL` predicate.
- It composes naturally with the existing `RESERVED_PROPERTY_KEYS` mechanism.

Edge-label-suffix (`:WORKS_AT_DEPRECATED`) was rejected because doubling label space conflicts with ADR-0021's regex; tombstone-anchored marker (`:DEPRECATED_EDGE` self-loop) was rejected because every read pays an outer-join check; Core-unaware was rejected because L3 capacity reads against Core would not honor the pivot's "every layer defaults skip deprecated" contract.

The L3-needs-filter argument is the deciding factor. L3 capacity-state queries hit Core directly. If Core doesn't filter, L3 has to wrap; that creates a cross-layer inconsistency where reads filter at KL but not at L3 unless L3 reimplements. Centralising the filter at Core unifies behaviour.

## Consequences

**Good:**

- Pivot's "every layer defaults `include_deprecated=False`" contract holds uniformly.
- KL's `MetagraphView` simplifies — filtering is Core-level, KL doesn't reimplement.
- L3 capacity reads honour the filter automatically (just call Core's iterators).
- Audit gate has a clean Cypher query for "deprecated since last release" (`WHERE e.deprecated_at >= $release_proposed_at`).
- Reversibility is trivial.

**Tradeoffs:**

- Two new reserved property keys. Documented; small reservation.
- Every Core read API gains a parameter. Default value preserves backward compat.
- Filter semantics for `disputed_at` differ from `deprecated_at` (disputed not filtered by default). Worth a callout in the docs to avoid confusion.
- Hyperedges with deprecated members: the hyperedge itself is not auto-deprecated. KL is responsible for deprecating the hyperedge if all members should be hidden.
- Loader behavior gotcha: load-with-filter-then-iterate-without doesn't expose deprecated edges. Documented.

**Coordinated changes:**

- `mindsos_core/models/edge.py` — `deprecated_at`, `disputed_at` fields.
- `mindsos_core/models/hyperedge.py` — same.
- `mindsos_core/models/metaedge.py`, `metahyperedge.py` — same.
- `mindsos_core/schema/validation.py` — adds two reserved property keys.
- `mindsos_core/models/graph.py` — `iter_edges(include_deprecated=False)` etc.
- `mindsos_core/models/metagraph.py` — `iter_metaedges(include_deprecated=False)` etc., plus `iter_xrefs(include_deprecated=False)` (per ADR-0128).
- `mindsos_core/reconstruction/graph_loader.py` — `load(include_deprecated=False)`.
- `mindsos_core/exceptions.py` — `CompositionalImmutableError` (joins ADR-0117's surface).
- KL: `MetagraphView` passes through; KL deprecation API (ADR-0116) writes the properties.
- Pivot ADR-0115 [Reserved]: audit gate queries deprecated edges.
- Tests: `tests/unit/core/test_soft_delete.py`, `tests/unit/core/test_iter_edges_filter.py`.
- Documentation: `docs/concepts/global-local.md` (deprecate vs delete), `docs/dev/internals/core.md` (filter pattern).

## Alternatives considered

1. **Edge-label suffix (`:WORKS_AT_DEPRECATED`).** Rejected — doubles label space; conflicts with rel-type regex (ADR-0021); migration of existing edges is heavy.
2. **Tombstone-anchored marker (`:DEPRECATED_EDGE` self-loop).** Rejected — every read pays an outer-join check; complicates the loader; reuses tombstone mechanism for unrelated semantics.
3. **Core stays unaware; deprecation is KL-only.** Rejected — L3 capacity reads bypass KL; pivot's uniform-default contract fails.
4. **Single `status: enum` property** (`active | deprecated | disputed`). Rejected — loses the timestamp (`deprecated_at` is useful for audit gate's "deprecated since release N" query); single enum can't express "both deprecated AND disputed."
5. **Three-state with timestamps but consolidated property name.** Rejected — `disputed_at` and `deprecated_at` are independent (an edge can be disputed first and later deprecated); separate properties match the natural semantics.

## Implementation references

- `mindsos_core/models/edge.py` and siblings — new fields.
- `mindsos_core/schema/validation.py` — reserved keys.
- Loader and iterator updates listed above.
- KL: `mindsos_knowledge/views.py` (MetagraphView passes through), forthcoming `kl.deprecate_edge(...)` API per ADR-0116.
- Pivot: `mindsos_server/audit_gate.py` (per ADR-0115) queries deprecated edges.
- Tests: `tests/unit/core/test_soft_delete.py`.
- Documentation: `docs/concepts/global-local.md`, `docs/dev/internals/core.md`, `docs/api/core/edge.md`.

ADR moves from Proposed to Accepted when soft-delete properties land on Core edges, default-filter parameters propagate through the read APIs, and `docs/concepts/global-local.md` documents the model.

## Revisions

1. **2026-05-16 (Phase 10 — M5 + M6 + M11; D1-rev compositional clause strip).** Substrate + iterator/loader filter ship together (P68 merge of original Phase 10 substrate scope with Phase 11 filter pass). Soft-delete fields land on `Edge` / `HyperEdge` / `MetaEdge` / `MetaHyperEdge` (4 edge variants per SOFT_DELETE_AUDIT_NOTE; IntergraphEdge / IntergraphHyperEdge are out of scope per P83). XRef restores `target_stale` + `deprecated_at` (Phase 09 P53 reversal). 20 setter methods on Graph / Metagraph quartet + XRef PX2 quartet. State-file v=4 → v=5 bumps (metagraph + graph). 22 cypher builders (PB-4a per-method). The original "CompositionalMetaEdge rejects soft-delete with CompositionalImmutableError" clause is **stripped** (D1-rev): halvim slim port dropped CompositionalMetaEdge entirely (N3-D); the class survives per ADR-0148 IntergraphEdge consumer, but its consumer is `IntergraphEdge.compositional` checks, not soft-delete refusal. Status flips Proposed → Accepted.
