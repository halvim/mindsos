---
last_confirmed_phase: 04-v2
---

# `mindsos_core.HyperEdge`

An n-ary, **typed** (Phase 04-v2 — ADR-0017 / MC-2) relationship across
an arbitrary set of `Node`s. Phase 03 slim port — drops the soft-delete
fields (Phase 10).

> **Code location:** `HyperEdge` ships in `mindsos_core/models/edge.py`
> next to `Edge` (matches the parent project's layout). The doc page is
> kept separate for reader ergonomics — this is a deliberate doc/code
> divergence.

## Dataclass fields

| Field | Type | Default | Description |
|---|---|---|---|
| `nodes` | `Set[Node]` | `set()` | Member nodes. Empty set raises `SchemaError` in `__post_init__`. |
| `type_name` | `str` | `""` | **Phase 04-v2 — required.** Cypher rel-type regex per ADR-0021 enforced at `__post_init__` (the SENT-1 sentinel `"UNSPECIFIED"` is a deliberate regex fit for legacy v=1/v=2 rehydration). |
| `label` | `Optional[str]` | `None` | Optional human-readable label. |
| `edge_id` | `str` | UUID4 | Stable id. |
| `properties` | `Dict[str, Any]` | `{}` | Open property dict. |

## Empty members invariant

```python
from mindsos_core import HyperEdge, SchemaError

HyperEdge(nodes=set())            # raises SchemaError
HyperEdge(nodes={n}, label="x")   # ok (one member is fine)
```

## Member ordering canonicalisation

In-memory `nodes` is a `Set[Node]` and therefore unordered. When
serialised to the state file (or future Cypher), members are written as
`sorted(node_id for node in he.nodes)`. This makes:

* Two state files of the same hyperedges produce byte-identical JSON.
* Existence tests (`is hyperedge {a,b,c} present?`) sort-invariant by
  construction.
* Diff noise from insertion-order changes eliminated.

## Identity semantics

`HyperEdge.__hash__` hashes `edge_id`; `__eq__` compares `edge_id`. Two
hyperedges with the same member set but different `edge_id`s are
distinct.

## Updating `type_name` post-create (Phase 04-v2 — UHT-1)

`Graph.update_hyperedge_type(edge_id, new_type_name)` (Python) /
`mindsos graph update-hyperedge-type --hyperedge-id ID --type T` (CLI)
updates a hyperedge's `type_name`. Cypher rel-type regex applies;
schema validation runs if attached.

This is asymmetric with `Edge` and `Node`, whose `type_name` remains
immutable after creation. The asymmetry is intentional: Phase 04-v2
introduces a new top-level field on `HyperEdge` mid-stream; legacy
v=1/v=2 hyperedges loaded under SENT-1 carry the `UNSPECIFIED`
sentinel and need a recovery path. `Edge` / `Node` have no analogous
legacy-migration concern.

## What's not in Phase 03 / Phase 04-v2

* `deprecated_at` / `disputed_at` soft-delete fields (ADR-0133) — Phase 10.
* `iter_hyperedges(include_deprecated=...)` — Phase 10.
