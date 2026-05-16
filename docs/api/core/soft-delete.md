---
last_confirmed_phase: 10
---

# `mindsos_core` — Soft-delete API

20 setter methods + filter parameter on every read API. Per ADR-0133 + ADR-0128 + ADR-0135.

Concept overview: [Soft-delete](../../concepts/soft-delete.md).

## Setter quartet pattern

Every soft-deletable element kind has 4 setter methods: `deprecate_*` / `undeprecate_*` / `dispute_*` / `undispute_*`. The `deprecate_*` and `dispute_*` variants take a keyword-only `at: datetime | None = None` — `None` resolves to `datetime.now(timezone.utc)`. All return the mutated dataclass instance.

## `Graph` — Edge quartet

```python
g.deprecate_edge(edge_id, *, at=None) -> Edge
g.undeprecate_edge(edge_id) -> Edge
g.dispute_edge(edge_id, *, at=None) -> Edge
g.undispute_edge(edge_id) -> Edge
```

Raises `IdentityError` if `edge_id` is not in `g.edges`.

## `Graph` — HyperEdge quartet (fixes SD1)

```python
g.deprecate_hyperedge(hyperedge_id, *, at=None) -> HyperEdge
g.undeprecate_hyperedge(hyperedge_id) -> HyperEdge
g.dispute_hyperedge(hyperedge_id, *, at=None) -> HyperEdge
g.undispute_hyperedge(hyperedge_id) -> HyperEdge
```

Phase 10 closes the v3-baseline SD1 gap — HyperEdge had no mutation API.

## `Metagraph` — MetaEdge quartet (fixes SD2 + SD3)

```python
mg.deprecate_metaedge(metaedge_id, *, at=None) -> MetaEdge
mg.undeprecate_metaedge(metaedge_id) -> MetaEdge
mg.dispute_metaedge(metaedge_id, *, at=None) -> MetaEdge
mg.undispute_metaedge(metaedge_id) -> MetaEdge
```

Phase 10 SD2 fix — v3 baseline shipped a single `deprecate_metaedge(*, at=None)` overload; Phase 10 ships the full quartet matching Graph's pattern. SD3 fix — `dispute_metaedge` exists for the first time.

## `Metagraph` — MetaHyperEdge quartet

```python
mg.deprecate_metahyperedge(metahyperedge_id, *, at=None) -> MetaHyperEdge
mg.undeprecate_metahyperedge(metahyperedge_id) -> MetaHyperEdge
mg.dispute_metahyperedge(metahyperedge_id, *, at=None) -> MetaHyperEdge
mg.undispute_metahyperedge(metahyperedge_id) -> MetaHyperEdge
```

## `Metagraph` — XRef quartet (PX2)

```python
mg.mark_xref_stale(xref_id) -> XRef          # sets target_stale = True
mg.unmark_xref_stale(xref_id) -> XRef        # sets target_stale = False
mg.deprecate_xref(xref_id, *, at=None) -> XRef
mg.undeprecate_xref(xref_id) -> XRef
```

No `dispute_xref` / `undispute_xref` — XRef does not carry `disputed_at` per ADR-0128 amendment-3.

`mark_xref_stale` is also called by `Metagraph.remove_graph(force=True)` per ADR-0135 to invalidate incoming XRefs whose target is being removed.

## Iterator + loader filter

Every iterator gains `include_deprecated: bool = False`:

```python
list(g.iter_edges())                           # filters deprecated_at != None
list(g.iter_edges(include_deprecated=True))    # passes everything

list(mg.iter_metaedges())
list(mg.iter_metahyperedges())
list(mg.iter_xrefs())     # AND-composes with source_id / target_metagraph_id / etc.
```

Loaders mirror:

```python
load_graph(client, gid, include_deprecated=False)
load_metagraph(client, mid, include_deprecated=False)
MetagraphLoader(client).load(mid, include_deprecated=False)
MetagraphLoader(client).refresh(mg, role, include_deprecated=False)
iter_load_graph(client, gid, include_deprecated=False)
```

Loader filter applies at Cypher level — deprecated rows are not materialized.

## Helpers

### `_resolve_at`

```python
from mindsos_core.persistence.soft_delete import _resolve_at
```

Centralized timestamp resolver. `_resolve_at(None)` returns `datetime.now(timezone.utc)`; `_resolve_at(dt)` passes through.

### `SoftDeleteKind` enum

```python
from mindsos_core import SoftDeleteKind
# SoftDeleteKind.EDGE, .HYPEREDGE, .METAEDGE, .METAHYPEREDGE, .XREF
```

Typed keys for `Metagraph._soft_delete_dirty` + `Graph._soft_delete_dirty` (P72 — typo-proof drain).

### `BlockedReason` enum

```python
from mindsos_core import BlockedReason
# BlockedReason.DANGLING_REFS, .INCIDENT_META_EDGES_CASCADE_FALSE
```

Distinguishes the two `RemoveGraphBlockedError` raise paths.

## See also

* [Concept — soft-delete](../../concepts/soft-delete.md)
* [API — MetagraphSnapshot](metagraph-snapshot.md)
* [API — Metagraph (remove_graph)](metagraph.md)
* [ADR-0133](../../decisions/adr/0133-soft-delete-via-deprecated-disputed-properties.md)
