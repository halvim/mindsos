---
last_confirmed_phase: 05a
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
* `remove_graph(graph_id: str) -> None` — P19 always-cascade slim:
  removes incident metaedges + metahyperedges first, then the graph
  itself. No `cascade` parameter, no `force` flag, no `RemovalImpact`
  return — Phase 10 reintroduces.

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
