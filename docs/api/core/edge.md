---
last_confirmed_phase: 03
---

# `mindsos_core.Edge`

A directed, typed binary relationship between two `Node`s. Introduced as
a Phase 03 slim port; the `_version` field (Phase 07) and the soft-delete
fields `deprecated_at` / `disputed_at` (Phase 10) are now live.

## Dataclass fields

| Field | Type | Default | Description |
|---|---|---|---|
| `source` | `Node` | — | Origin node. |
| `target` | `Node` | — | Destination node. |
| `type_name` | `str` | — | Cypher relationship type — must match `^[A-Z][A-Z0-9_]{0,63}$` (ADR-0021). Validated by `Graph.add_edge`. |
| `label` | `Optional[str]` | `None` | Optional human-readable label. |
| `edge_id` | `str` | UUID4 | Stable id. |
| `properties` | `Dict[str, Any]` | `{}` | Open property dict. |
| `_version` | `int` | `1` | Monotonic OCC version counter (ADR-0127). Added Phase 07. |
| `deprecated_at` | `Optional[datetime]` | `None` | Soft-delete timestamp (ADR-0133). Added Phase 10. |
| `disputed_at` | `Optional[datetime]` | `None` | Dispute timestamp (ADR-0133). Added Phase 10. |

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

## History

* `_version` field (ADR-0127 OCC) — added Phase 07.
* `deprecated_at` / `disputed_at` soft-delete fields (ADR-0133) — added Phase 10 (now live, see table above).
* `iter_edges(include_deprecated=...)` / `deprecate_edge` /
  `undeprecate_edge` / `dispute_edge` / `undispute_edge` — added Phase 10; see [soft-delete.md](soft-delete.md).
