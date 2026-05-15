---
last_confirmed_phase: 09
---

# `mindsos_core` — XRef API

The `XRef` primitive + the `Metagraph` methods that produce them, the
repository that persists them, the loader that reconstructs them, the
migration helper for legacy `ref:global_*` data, and the
`XRefIntegrityError` raised on validation failure.

ADR backing: [ADR-0128](../../decisions/adr/0128-hybrid-xref-cross-metagraph-refs.md).
Concept overview: [References — hybrid model](../../concepts/references.md).

## Class — `XRef`

```python
from mindsos_core import XRef
```

Frozen dataclass (in spirit — `kw_only=True` for safe field reorders;
`__hash__` + `__eq__` keyed by `xref_id`).

### Fields (8)

| Field | Type | Notes |
|-------|------|-------|
| `source_metagraph_id` | `str` | id of the metagraph the source element lives in |
| `source_id` | `str` | id of the source `:Node` / `:Edge` / `:HyperEdge` |
| `target_metagraph_id` | `str` | id of the metagraph the target element lives in |
| `target_role` | `str` | role of the target graph (`"lexicon"`, `"concepts"`, etc.) |
| `target_id` | `str` | id of the target element |
| `ref_type` | `str` | KL `REF_TYPES` vocabulary entry (Core does not enforce) |
| `xref_id` | `str` | UUID4 stable across the lifetime of this XRef (auto-minted if not supplied) |
| `properties` | `dict[str, Any]` | optional per-XRef property bag; reserved-key-aware |

`target_stale` and `deprecated_at` from the v3 baseline are **not
present** at Phase 09 (deferred to Phase 10 alongside their setters).

## `Metagraph.add_xref` — programmatic construction

```python
def add_xref(
    self,
    *,
    source_id: str,
    target_metagraph_id: str,
    target_role: str,
    target_id: str,
    ref_type: str,
    properties: Optional[Dict[str, Any]] = None,
    target_metagraph: Optional["Metagraph"] = None,
) -> XRef:
    ...
```

Validation runs **before** the WAL entry is opened:

1. `source_id` must be registered in this metagraph's identity registry.
2. If `target_metagraph` is supplied, the target id must exist in a
   contained graph with matching `target_role`. Otherwise raises
   `XRefIntegrityError`. When `target_metagraph` is `None`, the XRef
   is accepted as "soft".
3. `properties` are validated against the reserved-key /
   primitive-only contract.

Then the in-memory state is populated (XRef minted, identity
register, `mg.xrefs` insert, both inverse indexes populated). Then
the persistence path:

- If `mg._persist_client` is set (loader-attached metagraph), an
  inline WAL+DB write fires via `XRefRepository.persist`. The XRef is
  not marked dirty (it's already persisted).
- If not, only `mg._xrefs_dirty` is updated. The next
  `MetagraphRepository.persist(mg)` drains the dirty set.

## `Metagraph.iter_xrefs` — filtered iteration

```python
def iter_xrefs(
    self,
    *,
    source_id: Optional[str] = None,
    target_metagraph_id: Optional[str] = None,
    target_id: Optional[str] = None,
    ref_type: Optional[str] = None,
) -> Iterator[XRef]:
    ...
```

Filters AND-compose; unset = wildcard. Internally:

- `source_id` set → uses `_xrefs_by_source` index for the seed.
- `target_metagraph_id` AND `target_id` both set → uses
  `_xrefs_by_target` compound index.
- Otherwise full scan; remaining filters apply post-fetch.

## `Metagraph.remove_xref(xref_id)`

Removes the XRef from `mg.xrefs` + both inverse indexes + identity
registry + dirty set. If `mg._persist_client` is set, also runs a
WAL-wrapped `DETACH DELETE` inline. Raises `IdentityError` if
`xref_id` is unknown.

## `XRefRepository`

```python
from mindsos_core.persistence import XRefRepository
```

```python
repo = XRefRepository(client)
repo.persist(xref)                     # WAL-wrapped MERGE :XRef + :XREF_OF
repo.remove(xref_id, source_metagraph_id=...)   # WAL-wrapped DETACH DELETE
```

WAL entries open + commit on success per [ADR-0122](../../decisions/adr/0122-wal-graph-for-multi-statement-write-safety.md).
Crashes mid-write leave the entry uncommitted; the next
`recover(client, mid)` replays via the registered MERGE-based
replayer.

## `XRefLoader`

```python
from mindsos_core.reconstruction import XRefLoader

XRefLoader(client).load_into(mg)
```

Clear-first semantics: empties `mg.xrefs` + both inverse indexes +
identity-unregisters every existing XRef id + clears
`mg._xrefs_dirty`, then re-populates from the DB query
`MATCH (x:XRef {source_metagraph_id: $mid})`. Direct dict
assignment bypasses `mg.add_xref` (so no inline WAL+DB writes during
load).

## `attach_xref_loader`

```python
from mindsos_core.reconstruction import attach_xref_loader

handle = attach_xref_loader(mg)
```

Idempotent helper. Subscribes a callback to
`mg.register_after_load_observer` that reads `mg._persist_client` at
fire time and runs `XRefLoader(client).load_into(mg)`. The
`MetagraphLoader.load` / `.refresh` paths set `_persist_client`
transiently before firing after-load observers, so this helper is the
typical wiring for keeping `mg.xrefs` in sync with FalkorDB.

## `migrate_in_memory`

```python
from mindsos_core.persistence.xref_migration import migrate_in_memory

n_created = migrate_in_memory(
    mg, target_metagraph_id="...", default_ref_type="SPECIALISES",
)
```

Walks every node in `mg`, converting each `ref:global_<role>=<id>`
property to a fresh `XRef`. Drops the migrated property strings + the
sibling `ref_type` property after each successful migration. Sets
`mg.properties["xref:migrated_at"]` on whole-loop completion;
re-runs short-circuit immediately. Per-XRef content-tuple dedup
handles partial-crash recovery.

Programmatic-only at Phase 09; no CLI verb. Production trigger is
the Server first-start hook in a later phase
([ADR-0142](../../decisions/adr/0142-xref-cutover-for-ref-global.md)).

## Exceptions

### `XRefIntegrityError`

```python
from mindsos_core.exceptions import XRefIntegrityError
```

Subclass of `PersistenceError`. Raised by `Metagraph.add_xref` when
`target_metagraph` is supplied AND the target is not registered.
Validation runs before the WAL entry opens, so the rejected write
never enters the WAL (no resurrection on next `recover()`).

### `WALReplayerMissingError`

Raised by `recover(client, mid)` when an uncommitted `:WALEntry` row
has a `kind` not present in `client._replayers`. Phase 09 ships the
loud-fail contract — the Phase 08 silent narrow-catch was removed
(the L1 replayers are now registered on `FalkorClient` construction
via `register_all_l1_replayers`, so an unknown kind is a real bug).

## Related

- [Concept: References — hybrid model](../../concepts/references.md)
- [Internals: Core layer — Persistence + Reconstruction](../../dev/internals/core.md)
- [ADR-0128](../../decisions/adr/0128-hybrid-xref-cross-metagraph-refs.md) — hybrid XRef primitive
- [ADR-0142](../../decisions/adr/0142-xref-cutover-for-ref-global.md) — cutover plan for `ref:global_*` user data
