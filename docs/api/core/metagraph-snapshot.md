---
last_confirmed_phase: 10
---

# `mindsos_core` — `MetagraphSnapshot`

In-memory snapshot/restore helper for `Metagraph`. Phase 10 slim-port from v3 (271 LoC). Per [ADR-0027](../../decisions/adr/0027-metagraph-snapshot-restore-in-place.md) + [ADR-0028](../../decisions/adr/0028-metagraph-snapshot-not-serialisable.md) + [ADR-0129](../../decisions/adr/0129-metagraph-snapshot-narrowed-to-release-ship.md).

Dev-internal companion: [Snapshot internals](../../dev/internals/snapshots.md).

## Scope warning

```python
from mindsos_core import MetagraphSnapshot
```

Per ADR-0129 the **sole supported caller in v1 is `mindsos_server.release.release_update`** — used to bracket the canonical-Global FalkorDB write inside a release-ship operation under `RELEASE_SHIP_LOCK`. Other callers should use the WAL graph (ADR-0122) for multi-statement write safety.

Phase 10 ships:
* Docstring + module-level deprecation note on `mindsos_core.metagraph_snapshot`.
* No CI lint rule yet (deferred to Phase 18+ per Q lock).

## API surface — 2 methods

### `MetagraphSnapshot.of(mg) -> MetagraphSnapshot`

Construct a deep-copied snapshot of `mg`'s mutable state.

```python
snap = MetagraphSnapshot.of(mg)
```

Captures the 12-attribute allow-list (M3 + P84):

| Attribute | Source | Purpose |
|---|---|---|
| `_metagraph_id` | `mg.metagraph_id` | post-restore mismatch guard |
| `_metagraph_props` | `mg.properties` | ADR-0130 Metagraph property bag |
| `_graphs` | `mg.graphs` | per-graph attribute-level deep-copy via `_GraphSnap` |
| `_metaedges` | `mg.metaedges` | full deep-copy |
| `_metahyperedges` | `mg.metahyperedges` | full deep-copy |
| `_intergraph_edges` | `mg.intergraph_edges` | P84 — Phase 05b primitive |
| `_intergraph_hyperedges` | `mg.intergraph_hyperedges` | P84 — Phase 05c primitive |
| `_schema_name` | `mg.schema_name` | P84 — schema attach state |
| `_schema` | `mg.schema` | P84 — cached MetagraphSchema reference (immutable share) |
| `_xrefs` | `mg.xrefs` | ADR-0128 XRef rows |
| `_xrefs_dirty` | `mg._xrefs_dirty` | RB1 — pre-existing-dirty state survives restore |
| `_soft_delete_dirty` | `mg._soft_delete_dirty` | RPB-11 — Phase 10 dirty buckets |
| `_identity_ids` | `mg.identity.ids` | rebuilt via `IdentityRegistry.clear()+register()` on restore |

Per-`_GraphSnap`:
* `properties` — P85 graph-side property bag.
* `soft_delete_dirty` — P86 graph-side dirty buckets (EDGE + HYPEREDGE).

**Not captured:**
* `_persist_client` — shared by reference per V3 (transient field, irrelevant to state).
* Observer lists (`_remove_observers`, `_persist_observers`, …) — per-process subscriptions, not state.

### `snap.restore_into(mg) -> None`

Mutate `mg` back to the snapshotted state **in place** (ADR-0027). Identity preservation contract:

* `id(mg)` preserved — KL's `installed_locals[user_id] = mg` references stay valid.
* `id(mg.identity)` preserved — `IdentityRegistry.clear()` empties the shared `_ids` set without replacing the registry object (ADR-0020).
* `id(mg.graphs[gid])` preserved for surviving graphs (added-after-snapshot graphs are dropped; removed graphs are rebuilt as fresh Graph instances).

Raises `ValueError` if `mg.metagraph_id != snap._metagraph_id`.

## Constraints (ADR-0028)

* **Not serializable.** No `to_json()` / `from_json()`. Pickle is untested + forbidden in docstring.
* **In-process only.** Snapshot lives in the calling Python process; not durable across crashes. For crash-safety, use WAL graph (ADR-0122).
* **Session-scoped.** Snapshots are typically taken-and-restored within the lifetime of a single `release_update` critical section.

## Gotcha — load + restore interaction

`MetagraphLoader.load` clears `_soft_delete_dirty` post-load (PB-6a — loaded data is already in DB; dirty must be empty). If you snapshot BEFORE a load and restore AFTER, the snapshotted `_soft_delete_dirty` re-populates — and a subsequent persist would re-emit those writes. Document this in calling code if the order matters.

## See also

* [Concept — soft-delete](../../concepts/soft-delete.md)
* [Dev internals — Snapshot module](../../dev/internals/snapshots.md)
* [ADR-0027](../../decisions/adr/0027-metagraph-snapshot-restore-in-place.md)
* [ADR-0028](../../decisions/adr/0028-metagraph-snapshot-not-serialisable.md)
* [ADR-0129](../../decisions/adr/0129-metagraph-snapshot-narrowed-to-release-ship.md)
