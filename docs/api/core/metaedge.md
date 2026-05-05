---
last_confirmed_phase: 05a
---

# `MetaEdge` API

```python
from mindsos_core import MetaEdge
```

A directed, typed relationship between two contained `Graph` objects.

## Dataclass shape (Phase 05a, P1 + P8 + P9 + P11)

```python
@dataclass(kw_only=True)
class MetaEdge:
    source_graph_id: str       # graph_id of source (must be contained)
    target_graph_id: str       # graph_id of target (must differ from source — P15)
    type_name: str             # cypher rel-type (ADR-0021 regex enforced)
    label: Optional[str] = None
    edge_id: str = field(default_factory=generate_uuid)
    properties: Dict[str, Any] = field(default_factory=dict)
```

* **P1** — soft-delete fields (`deprecated_at` / `disputed_at`)
  intentionally absent in 05a; Phase 10 adds across all 4 edge variants
  uniformly.
* **P8** — `kw_only=True`; positional construction raises `TypeError`.
* **P9** — `__post_init__` runs `validate_edge_type_identifier(type_name)`
  (ADR-0021) at the dataclass boundary. Direct construction with a
  lowercase `type_name` raises `CypherError` regardless of whether the
  factory was used.
* **P11** — `source_graph_id` / `target_graph_id` are STRINGS (the
  graph's `graph_id`), not `Graph` objects. The factory looks up
  containment in `mg.graphs`.

## Persisted shape (in metagraph state file v=1)

```json
{
  "edge_id": "...",
  "source_graph": "<graph-name>",
  "target_graph": "<graph-name>",
  "type_name": "REFINES",
  "label": "...",
  "properties": {"...": "..."}
}
```

Persistence stores graph **names** (not graph_ids) for readability and
locality; the `_state_to_metagraph` rehydrator translates name→id at
load time.

## Equality / hash

By `edge_id` only. Two `MetaEdge` instances with the same `edge_id` are
equal regardless of source/target/type/properties.
