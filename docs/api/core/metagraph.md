---
last_confirmed_phase: 10
---

# `Metagraph` API

```python
from mindsos_core import Metagraph
```

## Constructor

```python
Metagraph(
    name: str,
    *,
    identity: Optional[IdentityRegistry] = None,
    metagraph_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    id_strategy: Optional[IdStrategy] = None,
)
```

* `name` — human-readable.
* `metagraph_id` — explicit id (used during reconstruction); defaults to
  fresh UUID4.
* `properties` — namespaced ADR-0130 property bag. Reserved keys at
  metagraph scope (P13): `metagraph_id`, `_state_version`,
  `contained_graphs`, `metaedges`, `metahyperedges`, `metagraph_name`.
* `id_strategy` — applies to metagraph-level mints (per P16, contained
  graphs keep their own per-graph strategies).

## Methods

### Graph membership

* `add_graph(graph: Graph) -> Graph` — unifies the graph's
  `IdentityRegistry` with the metagraph's. Q5-A eager id-collision
  check. P16 invariants: `g.identity is mg.identity` post-call;
  `g.id_strategy` untouched.
* `remove_graph(graph_id, *, cascade=True, force=False) -> RemovalImpact` —
  Phase 10 [ADR-0135](../../decisions/adr/0135-removal-impact-on-remove-graph.md) full surface.
  Returns a `RemovalImpact` (4 fields: `incoming_xrefs`,
  `incoming_ref_properties`, `proceeded`, `blocked_reason`) describing
  cross-graph refs pointing into the graph being removed. Two block paths
  raise `RemoveGraphBlockedError` (carrying `.impact` + `.blocked_reason`):
    * **`BlockedReason.DANGLING_REFS`** — `force=False` AND impact
      non-empty. `force=True` proceeds and stamps `target_stale=True` on
      each incoming XRef via `mark_xref_stale`.
    * **`BlockedReason.INCIDENT_META_EDGES_CASCADE_FALSE`** —
      `cascade=False` AND incident MetaEdges/MetaHyperEdges exist.
      **Independent of `force`** per Phase 10 P81 — `force=True` overrides
      only the dangling-refs gate, not the cascade gate.

  Compositional precheck (Phase 05b Pushback 17-A) still raises
  `CompositionalImmutableError` before either Phase 10 gate fires.

### Soft-delete setters (Phase 10)

* `deprecate_metaedge(metaedge_id, *, at=None) -> MetaEdge` — SD2 fix.
* `undeprecate_metaedge(metaedge_id) -> MetaEdge`.
* `dispute_metaedge(metaedge_id, *, at=None) -> MetaEdge` — SD3 fix.
* `undispute_metaedge(metaedge_id) -> MetaEdge`.
* `deprecate_metahyperedge(...)` / `undeprecate_metahyperedge` /
  `dispute_metahyperedge` / `undispute_metahyperedge`.
* `mark_xref_stale(xref_id) -> XRef` — sets `target_stale=True`.
  Also called by `remove_graph(force=True)`.
* `unmark_xref_stale(xref_id) -> XRef`.
* `deprecate_xref(xref_id, *, at=None) -> XRef`.
* `undeprecate_xref(xref_id) -> XRef`.

See [Soft-delete API](soft-delete.md) for the full setter matrix.

### Metaedges (P11 — graph_id strings, not Graph objects)

* `add_metaedge(source_graph_id, target_graph_id, type_name, *,
   label=None, properties=None) -> MetaEdge` — P15 refuses self-loop.
* `remove_metaedge(edge_id: str) -> None`
* `update_metaedge_properties(edge_id, properties, *, replace=False) ->
   MetaEdge`
* `iter_metaedges() -> Iterator[MetaEdge]` (no filtering in 05a; Phase
  10 adds `include_deprecated`).

### Metahyperedges

* `add_metahyperedge(graph_ids: Iterable[str], *, type_name,
   label=None, properties=None) -> MetaHyperEdge` — P15 requires n ≥ 2.
* `remove_metahyperedge(edge_id: str) -> None`
* `update_metahyperedge_properties(edge_id, properties, *, replace=False)
   -> MetaHyperEdge`
* `iter_metahyperedges() -> Iterator[MetaHyperEdge]`

### Properties (ADR-0130)

* `mg.properties: Dict[str, Any]` — direct access. Validated through
  `validate_user_properties(scope="metagraph")` on assignment via the
  constructor and `update_*_properties`.

## Slim-port deferral list

Not in 05a; lands in subsequent phases:

* `Metagraph.mint_id(kind, content)` — Phase 05b (consumer = IntergraphEdge).
* `add_xref` / `iter_xrefs` / `remove_xref` (ADR-0128) — Phase 09.
* `instantiate_*` / `compose` (ADR-0024 / ADR-0025) — Phase 06
  (`mindsos_instances` package).
* `RemovalImpact` + `force=True` on `remove_graph` (ADR-0135) — Phase 10.
* Backward-compat aliases `_kl_active_graph_ids` / `user_id` — re-added
  in Phase 14 / Phase 18.
* `add_intergraph_edge` (binary) — Phase 05b.
* `add_intergraph_hyperedge` (n-ary) — Phase 05c.
* `MetagraphSchema` attachment — Phase 05b.
