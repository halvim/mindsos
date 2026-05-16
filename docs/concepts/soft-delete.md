---
last_confirmed_phase: 10
---

# Soft-delete

MindsOS distinguishes between **soft-delete** (admin retired but record kept) and **hard-delete** (record permanently removed). Phase 10 lands the soft-delete substrate on Core's edge primitives per [ADR-0133](../decisions/adr/0133-soft-delete-via-deprecated-disputed-properties.md).

## The two timestamps

Every soft-deletable element carries two `datetime | None` fields:

* **`deprecated_at`** — admin retired this element. Default reads skip it.
* **`disputed_at`** — admin marked this disputed but not yet retired. Default reads still surface it.

Setting one does not implicitly set the other. An element can be `disputed_at: 2026-05-01` first, then `deprecated_at: 2026-05-15` later. The `disputed_at` timestamp survives the transition.

## Which elements are soft-deletable

Phase 10 ships fields + setters for **4 edge variants** uniformly:

| Element | Lives on | Setter quartet |
|---|---|---|
| `Edge` | `Graph` | `deprecate_edge` / `undeprecate_edge` / `dispute_edge` / `undispute_edge` |
| `HyperEdge` | `Graph` | `deprecate_hyperedge` / `undeprecate_hyperedge` / `dispute_hyperedge` / `undispute_hyperedge` |
| `MetaEdge` | `Metagraph` | `deprecate_metaedge` / `undeprecate_metaedge` / `dispute_metaedge` / `undispute_metaedge` |
| `MetaHyperEdge` | `Metagraph` | `deprecate_metahyperedge` / `undeprecate_metahyperedge` / `dispute_metahyperedge` / `undispute_metahyperedge` |

**Not soft-deletable** in v1: `Node` (per ADR-0133 §"Edges only; nodes are not soft-deletable"), `IntergraphEdge`, `IntergraphHyperEdge` (Phase 10 P83 — revisit when KL consumer surfaces).

## `XRef` is different

`XRef` (cross-metagraph reference, [ADR-0128](../decisions/adr/0128-hybrid-xref-cross-metagraph-refs.md)) carries a related-but-distinct pair:

* **`target_stale: bool`** — set `True` when the target metagraph removes the graph containing `target_id` (also stamped by `Metagraph.remove_graph(force=True)` per [ADR-0135](../decisions/adr/0135-removal-impact-on-remove-graph.md)). Readers may surface stale XRefs as a redirect signal.
* **`deprecated_at: datetime | None`** — admin retired the XRef itself (symmetric with edge soft-delete).

XRef does **not** carry `disputed_at` (per ADR-0128 §Revisions amendment-3).

The XRef quartet: `mark_xref_stale` / `unmark_xref_stale` / `deprecate_xref` / `undeprecate_xref`.

## Default read filter

Every Core iterator and getter that returns edges accepts:

```python
include_deprecated: bool = False
```

Default `False` filters out elements with `deprecated_at is not None`. `disputed_at` does **not** filter — disputed elements remain visible by default (disputed = "this is wrong but the data is still here for now"; deprecated = "stop showing this").

For XRef iterators, `target_stale` also does **not** filter — callers may want to see invalidated refs for redirect logic.

Affected methods (signature gains `include_deprecated`):

* `Graph.iter_edges`, `Graph.iter_hyperedges`, `Graph.get_edges_for_node`
* `Metagraph.iter_metaedges`, `Metagraph.iter_metahyperedges`, `Metagraph.iter_xrefs`
* `GraphLoader.load`, `MetagraphLoader.load`, `MetagraphLoader.refresh`, `load_metagraph`, `iter_load_graph`

## Loader filter — the gotcha

When `GraphLoader.load(include_deprecated=False)` runs, deprecated edges are filtered **at the Cypher level** — they are not materialized into the in-memory `Graph` object. The loader does not carry the filter as state.

Consequence: loading a Graph with `include_deprecated=False` and then iterating with `include_deprecated=True` returns nothing extra (the deprecated edges were never loaded). To re-include them, reload with `include_deprecated=True`.

## Setter semantics

Setters take an optional keyword-only `at: datetime | None = None`. `None` resolves to `datetime.now(timezone.utc)` via the shared `_resolve_at` helper ([PB-2](../decisions/adr/0133-soft-delete-via-deprecated-disputed-properties.md)). Setters return the mutated dataclass instance (PB-10).

```python
edge = g.deprecate_edge(edge_id)  # returns mutated Edge with deprecated_at set
edge.deprecated_at  # datetime.now(timezone.utc) of the call
```

## Persistence

Soft-delete state persists to FalkorDB as row properties:

* `Edge` / `HyperEdge`: `deprecated_at` + `disputed_at` properties on the existing edge / hyperedge row.
* `MetaEdge` / `MetaHyperEdge`: same shape, on the metagraph-scoped rows.
* `XRef`: `target_stale` (bool) + `deprecated_at` (ISO string) on the `:XRef` row.

State-file persistence: metagraph state-file v=5 (`metaedges[]` + `metahyperedges[]` + `xrefs[]` entries gain the new keys); graph state-file v=5 (`edges[]` + `hyperedges[]` entries gain the new keys). Phase 10 ships forward-only migrations from v=4 to v=5 with sensible defaults (`None` / `False`).

## What's NOT in Phase 10

* **No CLI verbs for soft-delete.** Programmatic-only at L1. CLI surface is a future-phase scope question.
* **No IntergraphEdge / IntergraphHyperEdge soft-delete.** Out of scope per P83.
* **No Node soft-delete.** Per ADR-0133 §"Edges only".
* **Auto-firing of `mark_xref_stale` on archived-target detection** is deferred to Server first-start hook (Phase 18+ per ADR-0128 §Revisions amendment-3 + Phase 10 O1).

## See also

* [ADR-0133 — soft-delete representation](../decisions/adr/0133-soft-delete-via-deprecated-disputed-properties.md)
* [ADR-0128 — XRef + target_stale](../decisions/adr/0128-hybrid-xref-cross-metagraph-refs.md)
* [ADR-0135 — RemovalImpact + force-stamp](../decisions/adr/0135-removal-impact-on-remove-graph.md)
* [API — soft-delete setters](../api/core/soft-delete.md)
* [Dev internals — snapshot](../dev/internals/snapshots.md)
