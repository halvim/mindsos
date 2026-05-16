---
last_confirmed_phase: 10
---

# Snapshot — internals

Phase 10 slim-port of `mindsos_core/metagraph_snapshot.py` from v3 baseline. Dev-internal companion to the [public API](../../api/core/metagraph-snapshot.md).

## Why mutate-in-place (ADR-0027)

The Knowledge Layer stores each user's Local Metagraph by reference:

```python
installed_locals[user_id] = mg
```

Rolling a Metagraph back by **returning a fresh instance** would leave `installed_locals[user_id]` pointing at a dead object. The fix: deep-copy every mutable attribute INTO the existing `Metagraph` instance, never replacing it.

Same logic for `IdentityRegistry` (ADR-0020 — shared across all contained graphs) and surviving `Graph` objects (external layers may cache them).

## Restore-pass algorithm

1. **Validate identity.** Raise `ValueError` if `mg.metagraph_id != snap._metagraph_id`. The snapshot is bound to one specific Metagraph object.

2. **Restore Metagraph property bag.** `mg.properties.clear(); mg.properties.update(deepcopy(snap._metagraph_props))`.

3. **Restore graphs.** Three cases per `gid`:
   * **Survivor** (in both live and snap): mutate the existing Graph in place — `name`, `role`, `schema`, `nodes`, `edges`, `hyperedges`, `properties`, `_soft_delete_dirty` all restored via clear+update on the dict references. `id(g)` preserved.
   * **Added after snapshot** (in live, not in snap): `del mg.graphs[gid]`. The Graph object is dropped; external references hold a now-orphan.
   * **Removed before snapshot** (in snap, not in live): rebuild a fresh `Graph` with the snapshotted `graph_id`. External references to the original-pre-removal hold a stale pointer (ADR-0027 §"Bad" — documented hazard).

4. **Restore metaedges + metahyperedges.** Full deep-copy assignment (Phase 05a P11 — graph_id-string endpoints; no Graph-object rebinding pass needed unlike v3 baseline).

5. **Restore intergraph_edges + intergraph_hyperedges** (P84). Full deep-copy.

6. **Restore schema attach state** (P84). `mg.schema_name = snap._schema_name; mg.schema = snap._schema` (schema treated as immutable reference, same pattern as `Graph.schema`).

7. **Restore XRefs + inverse indexes.** Clear `mg.xrefs` + `_xrefs_by_source` + `_xrefs_by_target`, then re-populate from `snap._xrefs`. Rebuild inverse indexes by walking each XRef's `source_id` and `(target_metagraph_id, target_id)`.

8. **Restore dirty sets.** `_xrefs_dirty` (RB1) and `_soft_delete_dirty` (RPB-11) — both Metagraph-side and per-Graph Graph-side (P86).

9. **Rebuild IdentityRegistry.** `mg.identity.clear()` (ADR-0020 — preserves shared-registry object identity; empties `_ids` in place), then `mg.identity.register(uid)` for every snapshotted id.

## What lives in `_GraphSnap`

Per-graph attribute capture (not the whole `Graph` object) so survivors can be mutated in place:

| Field | Source | Notes |
|---|---|---|
| `graph_id` | `g.graph_id` | identity key |
| `name` | `g.name` | mutable |
| `role` | `g.role` | mutable |
| `schema` | `g.schema` | treated as immutable; shared by reference |
| `nodes` | `g.nodes` | deep-copy |
| `edges` | `g.edges` | deep-copy |
| `hyperedges` | `g.hyperedges` | deep-copy |
| `properties` | `g.properties` | P85 — graph-side property bag |
| `soft_delete_dirty` | `g._soft_delete_dirty` | P86 — Graph-side dirty (EDGE + HYPEREDGE buckets) |

## What's NOT captured

* `_persist_client` — transient field set/cleared by `MetagraphLoader` and `MetagraphRepository` around per-call lifecycle. Shared by reference per V3.
* Observer lists (`_remove_observers`, `_persist_observers`, `_after_load_observers`, `_graph_added_observers`) — per-process subscriptions. Restoring them would re-attach observers from a previous lifecycle.

## Phase 10 strips vs v3 baseline (PB-1)

Compared to `mindsos_core/metagraph_snapshot.py` in the project-root v3 source:

* **Strip `_PIGGYBACK_ATTRS` tuple** + `_piggyback: Dict[str, Any]` dataclass field + the two piggyback capture/restore loops. ADR-0130 Phase 09 acceptance ensures `_kl_active_graph_ids` and `mg.user_id` are real `mg.properties` keys; no more ad-hoc Python attributes to chase.
* **Strip the `_kl_active_graph_ids` skip-clause** in `.of()`. Closed by Phase 09 ADR-0130 Metagraph-side acceptance.
* **Strip `_element_instances` / `_composite_instances`** from the allow-list (P84). Per ADR-0132 instancing moved to `mindsos_instances`; those attributes don't exist on halvim's `Metagraph`.

## Phase 10 additions vs v3 baseline (PB-1)

* **`_xrefs_dirty` capture** (RB1). Phase 09 dirty-tracking survives the snapshot/restore cycle.
* **`_soft_delete_dirty` capture** (RPB-11). Phase 10 dirty-tracking at Metagraph scope.
* **`_GraphSnap.soft_delete_dirty`** (P86). Phase 10 dirty-tracking at Graph scope.
* **`_intergraph_edges` + `_intergraph_hyperedges`** (P84). Phase 05b/05c primitives.
* **`_schema_name` + `_schema`** (P84). Phase 05b schema attach state.

## Caller-side gotchas

### Load-then-restore interleaving

`MetagraphLoader.load` clears `_soft_delete_dirty` post-load (PB-6a) — loaded data is by definition already-persisted, so the dirty set must not re-emit it. If you take a snapshot BEFORE a load and restore AFTER, the snapshotted dirty buckets become live again. A subsequent `MetagraphRepository.persist` would then re-emit those soft-delete writes.

This is rarely the wrong thing — usually if you're restoring you want pre-load state back — but document if the order matters in calling code.

### Identity-after-restore

`mg.identity.clear()` followed by `register()` for every snapshotted id means the registry's internal data structure changes shape, but `id(mg.identity)` survives. External holders of `weakref.proxy(mg.identity)` continue to resolve.

`mg.graphs[gid]` survivor identity survives. Removed graphs are rebuilt with the same `graph_id` but a fresh Python object — external pre-removal references hold a stale pointer.

## See also

* [Public API — `MetagraphSnapshot`](../../api/core/metagraph-snapshot.md)
* [ADR-0027](../../decisions/adr/0027-metagraph-snapshot-restore-in-place.md)
* [ADR-0028](../../decisions/adr/0028-metagraph-snapshot-not-serialisable.md)
* [ADR-0129](../../decisions/adr/0129-metagraph-snapshot-narrowed-to-release-ship.md)
