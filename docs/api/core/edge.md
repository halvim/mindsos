---
last_confirmed_phase: 03
---

# `mindsos_core.Edge`

A directed, typed binary relationship between two `Node`s. Phase 03 slim
port — drops the soft-delete fields `deprecated_at` / `disputed_at`
(Phase 10).

## Dataclass fields

| Field | Type | Default | Description |
|---|---|---|---|
| `source` | `Node` | — | Origin node. |
| `target` | `Node` | — | Destination node. |
| `type_name` | `str` | — | Cypher relationship type — must match `^[A-Z][A-Z0-9_]{0,63}$` (ADR-0021). Validated by `Graph.add_edge`. |
| `label` | `Optional[str]` | `None` | Optional human-readable label. |
| `edge_id` | `str` | UUID4 | Stable id. |
| `properties` | `Dict[str, Any]` | `{}` | Open property dict. |

## ADR-0021 — Cypher rel-type validation

`type_name` is splice-into-Cypher data; allowing arbitrary strings is an
injection vector. `Graph.add_edge` calls `validate_edge_type_identifier`
before constructing the `Edge`. Invalid identifiers raise `CypherError`.

| `type_name` | Verdict |
|---|---|
| `WORKS_AT` | OK |
| `FOLLOWS` | OK |
| `REL_1` | OK |
| `works_at` | rejected (lowercase) |
| `Works_At` | rejected (mixed case) |
| `WORKS-AT` | rejected (hyphen) |
| `1WORKS` | rejected (digit prefix) |
| `""` | rejected (empty) |

## Identity semantics

`Edge.__hash__` hashes `edge_id`; `__eq__` compares `edge_id`. Two edges
between the same source/target with the same type but different
`edge_id`s are distinct.

## What's not in Phase 03

* `deprecated_at` / `disputed_at` soft-delete fields (ADR-0133) — Phase 10.
* `iter_edges(include_deprecated=...)` / `deprecate_edge` /
  `undeprecate_edge` / `dispute_edge` / `undispute_edge` — Phase 10.
