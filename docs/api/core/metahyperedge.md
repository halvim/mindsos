---
last_confirmed_phase: 05a
---

# `MetaHyperEdge` API

```python
from mindsos_core import MetaHyperEdge
```

An n-ary typed relationship across n ≥ 2 contained `Graph` objects.

## Dataclass shape (Phase 05a, P1 + P8 + P9 + P11 + P15)

```python
@dataclass(kw_only=True)
class MetaHyperEdge:
    graph_ids: List[str]       # n ≥ 2 contained graph_ids (P15); duplicates rejected
    type_name: str             # cypher rel-type (ADR-0021 regex)
    label: Optional[str] = None
    edge_id: str = field(default_factory=generate_uuid)
    properties: Dict[str, Any] = field(default_factory=dict)
```

* **P1** — soft-delete fields (`deprecated_at` / `disputed_at`) absent in
  05a; Phase 10 adds.
* **P8** — `kw_only=True`.
* **P9** — `__post_init__` runs `validate_edge_type_identifier(type_name)`.
* **P11** — `graph_ids` is `List[str]` (graph_ids), not `Set[Graph]`
  (parent shape).
* **P15** — `len(graph_ids) ≥ 2` enforced at dataclass boundary; n=1 is
  degenerate (`SchemaError`); n=0 raises (parent precedent).
  `len(set(graph_ids)) == len(graph_ids)` enforced (no duplicates).

## Persisted shape (in metagraph state file v=1)

```json
{
  "edge_id": "...",
  "type_name": "TRIO",
  "member_graphs": ["graph-name-a", "graph-name-b", "graph-name-c"],
  "label": "...",
  "properties": {"...": "..."}
}
```

`member_graphs` sorted by graph name (Q3-A) for byte-stable output.
Persistence uses graph **names** (not graph_ids).

## Equality / hash

By `edge_id` only.

## Notes vs `IntergraphHyperEdge` (05c)

`MetaHyperEdge` is **graph-level** — it relates n graphs as opaque units.
`IntergraphHyperEdge` (Phase 05c) is **node-level** — it relates n
anchor-nodes to m member-nodes across graphs (with a `compositional`
flag for identity-bearing composition like `cat = c+a+t`). The two
primitives serve different purposes; `MetaHyperEdge` is unaffected by
Phase 05b/05c.
