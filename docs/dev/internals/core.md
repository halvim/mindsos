---
last_confirmed_phase: 10
---

# Core layer internals — Persistence + Reconstruction (Phase 10)

This page documents the persistence-layer mechanics for `mindsos_core`.
The substrate decisions live in the ADRs at the project-root location
`docs/decisions/adr/` (not under `halvim_mindsos/`, per Model C hybrid
documented in [Repo layout](../repo-layout.md)).

Cross-references:

- [ADR-0030](../../decisions/adr/0030-client-protocol-minimal-sync.md) — Client Protocol contract.
- [ADR-0121](../../decisions/adr/0121-substrate-falkordb-for-graphs-sqlite-for-non-graph.md) — substrate commitment (umbrella).
- [ADR-0122](../../decisions/adr/0122-wal-graph-for-multi-statement-write-safety.md) — WAL graph.
- [ADR-0123](../../decisions/adr/0123-indexes-and-verify-integrity.md) — indexes + integrity scanner.
- [ADR-0126](../../decisions/adr/0126-async-client-via-thread-pool-wrapper.md) — AsyncClient via `asyncio.to_thread`.
- [ADR-0127](../../decisions/adr/0127-optimistic-concurrency-on-global-writes.md) — OCC on Global writes.
- [ADR-0130](../../decisions/adr/0130-property-bag-on-metagraph-graph.md) — `_props_json` encoding (Accepted in Phase 09).
- [ADR-0128](../../decisions/adr/0128-hybrid-xref-cross-metagraph-refs.md) — hybrid XRef primitive (Phase 09; Proposed until Phase 14 L2 consumer).
- [ADR-0142](../../decisions/adr/0142-xref-cutover-for-ref-global.md) — XRef cutover (Phase 09 ships L1 commitment).

## Phase 10 — Snapshot + soft-delete substrate + RemovalImpact + XRef setters

Phase 10 ships:

* **`MetagraphSnapshot`** ([ADR-0027](../../decisions/adr/0027-metagraph-snapshot-restore-in-place.md)) — slim-port from v3; 12-attribute allow-list (M3 + P84); mutate-in-place restore preserves `id(mg)` / `id(mg.identity)` / surviving `id(g)`. See [snapshot internals](snapshots.md).
* **`RemovalImpact` + `RemoveGraphBlockedError` + `BlockedReason` enum** ([ADR-0135](../../decisions/adr/0135-removal-impact-on-remove-graph.md)) — `remove_graph(*, cascade=True, force=False) -> RemovalImpact` with two block paths (DANGLING_REFS + INCIDENT_META_EDGES_CASCADE_FALSE; P81 independence).
* **Soft-delete substrate** ([ADR-0133](../../decisions/adr/0133-soft-delete-via-deprecated-disputed-properties.md)) — `deprecated_at` + `disputed_at` on `Edge` / `HyperEdge` / `MetaEdge` / `MetaHyperEdge`. XRef restores `target_stale` + `deprecated_at` (Phase 09 P53 reversal). 20 setter methods + iterator/loader filter pass (P68 merge).
* **22 cypher builders** (M16 + PB-4a per-method): 16 edge-side + 4 XRef + 2 impact-query.
* **10 WAL replayer kinds** (M8): 4 collapsed element-side + 4 XRef + Phase 09's 2 = 10. Wrapper grows 2 → 10 via composing `register_soft_delete_replayers` + extended `register_xref_replayers`.
* **State-file v=5** (M11): metagraph + graph state-file bumps. Per-element soft-delete fields persist as ISO strings + bool. Forward-only `_v4_to_v5` per kind (RR-7).
* **`mindsos persistence xref-list`** 8→10 fields (M24 + RR-6): JSON unconditional 10; Rich table grows columns only when non-default.

Caller surface: see [Soft-delete API](../../api/core/soft-delete.md) + [Concept overview](../../concepts/soft-delete.md).

## Phase 09 — XRef (cross-metagraph references)

**Storage shape.** `:XRef` rows live in the source metagraph anchored
by a `:XREF_OF` edge to the source `:Metagraph` row. Reverse lookups
use the indexed `(target_metagraph_id, target_id)` compound (no
edge traversal). The cascade contract is forward-only at Phase 09;
Phase 10 ships reverse-dangling cleanup.

**Indexes (4 new; bootstrap grows 14 → 18).**

| Label | Property | Purpose |
|-------|----------|---------|
| `:XRef` | `id` | primary lookup by xref_id |
| `:XRef` | `source_metagraph_id` | XRefLoader query (`MATCH (x:XRef {source_metagraph_id: $mid})`) |
| `:XRef` | `source_id` | forward walk (`mg.iter_xrefs(source_id=...)`) |
| `:XRef` | `(target_metagraph_id, target_id)` | reverse walk + `--target-metagraph` prefix-match |

**WAL replayers.** Phase 09 is the first phase to register actual L1
replayers. `register_all_l1_replayers(client)` (called by
`FalkorClient.__init__` after `bootstrap`) wires per-kind module
ownership: `mindsos_core/persistence/xref_repository.py::register_xref_replayers`
attaches `xref_add` (MERGE-based; idempotent) and `xref_remove`
(DETACH DELETE; idempotent) onto `client._replayers`. The
module-level `_REPLAYERS` global from Phase 07 is gone — replayers
are per-Client instance state, eliminating cross-test pollution.

**`recover()` failure mode change.** The Phase 08 silent narrow-catch
of `WALReplayerMissingError` in `MetagraphLoader.load` was removed
(Phase 09 P62). With actual L1 replayers registered, an unknown kind
in WAL is a real bug; the exception now propagates as
`PersistenceError`.

**Dirty-tracking on `Metagraph`.** `mg._xrefs_dirty: Set[str]` tracks
XRefs added programmatically without a `_persist_client` attached.
`MetagraphRepository.persist(mg)` drains this set after the standard
4-step lifecycle; atomic clear at end-of-loop survives partial-crash
retries (MERGE idempotency makes duplicate writes safe).

**State-file v=3 → v=4.** Adds `xrefs[]` array. `_v3_to_v4(state)`
in `mindsos_cli/migrations/metagraph.py` is single-line additive.
The `_state_to_metagraph` deserializer reads `xrefs[]` directly into
`mg.xrefs` + manually rebuilds `mg._xrefs_by_source` /
`mg._xrefs_by_target` inverse indexes, leaving `mg._xrefs_dirty`
empty (loaded XRefs are by definition already-persisted).

**`load --metagraph M` summary shape change.** The Phase 08 9-line
flat list is replaced by a single structured `Dependent state: ...`
key=value line that grows additively. Future phases that add new
buckets (Snapshots in Phase 10; integrity scanner output in Phase 11)
extend the same line; tests assert by key, not by position.

**XRefLoader subscription.** `attach_xref_loader(mg)` is the
idempotent helper that subscribes the loader to `mg`'s after-load
observer queue. The callback reads `mg._persist_client` at fire time
(set transiently by `MetagraphLoader.load` line 226 +
`.refresh` line 324). PB-9 clear-first semantics: every refresh
clears `mg.xrefs` + inverse indexes + identity registrations +
`_xrefs_dirty` BEFORE re-populating from the DB.

## Persistence layer

The persistence package lives at `mindsos_core/persistence/` and ships
five modules + a `reconstruction/graph_loader.py` sibling for the
single-Graph load path:

| Module | Surface |
|--------|---------|
| `client.py`         | `Client` Protocol, `FalkorClient`, `InMemoryClient`, `QueryResult` |
| `async_client.py`   | `AsyncClient` Protocol, `ThreadPoolAsyncClient` |
| `bootstrap.py`      | `bootstrap(client)`, `DEFAULT_INDEXES` (14 entries) |
| `graph_repository.py`     | `GraphRepository.persist` / `update_*_properties` / `remove_*` |
| `metagraph_repository.py` | `MetagraphRepository.persist` (4-step lifecycle) |
| `wal.py`            | `WriteAheadLog.entry(...)` context manager + raw `begin`/`commit`/`recover` |
| `integrity.py`      | `verify_invariants(mg)` (5 buckets) + `verify_invariants_graph(g)` (3 buckets) |
| `reconstruction/graph_loader.py` | `load_graph(client, graph_id) -> Graph` |

### Substrate

FalkorDB for graphs (per ADR-0121); SQLite for non-graph state (per
ADR-0004 amended). The Phase 07 persistence layer touches FalkorDB
only. JSON state files at `~/.mindsos/<kind>-<name>.json` remain the
authoritative tester surface (M0 B); FalkorDB is a queryable
projection populated by `mindsos persistence sync --graph X`.

The `Client` Protocol per ADR-0030 is intentionally minimal: three
methods (`run_query` / `run_batch` / `close`), no transactions, no
async, no per-call timeout. `run_batch` is sequential — failure on
statement N of M leaves 1..N-1 committed; recovery semantics live in
WAL (ADR-0122) and `MetagraphRepository.persist` 4-step lifecycle.

### WAL (ADR-0122)

Per-Metagraph write-ahead log realised as `:WALEntry` rows tagged
`metagraph_id`. Primary surface is the context-manager API:

```python
from mindsos_core.persistence import WriteAheadLog

wal = WriteAheadLog(client, metagraph_id="mg1")
with wal.entry(operation_id=uuid4().hex, kind="kl.propose_for_promotion",
               payload={"draft_id": "..."}) as op_id:
    # ... apply writes ...
    # __exit__ stamps committed=true on success;
    # on exception, the entry stays uncommitted for replay/compensate.
```

Raw `begin` / `commit` / `list_uncommitted` / `count_uncommitted` /
`gc` accessible for failure-injection tests (`RaisesOnNthCall` per
P20 B → P41 B → P82 A). Recovery: `recover(client, metagraph_id)`
iterates uncommitted entries and dispatches to replayers registered
via `register_replayer(kind, cb)`. Phase 07 ships the mechanism only —
no L1 consumer; L0/L2 wire replayers later.

### Indexes (ADR-0123)

`bootstrap(client)` creates 14 indexes idempotently per Phase 07 P95 B:

- **10 node-label `id` indexes**: `:Metagraph`, `:Graph`, `:Node`,
  `:HyperEdge`, `:MetaHyperEdge`, `:IntergraphHyperEdge`,
  `:ElementInstance`, `:CompositeInstance`, `:Tombstone` (indexed on
  `graph_id`), `:WALEntry` (on `operation_id`).
- **3 relationship-type `id` indexes** per ADR-0021: `:Edge`,
  `:MetaEdge`, `:IntergraphEdge`. Uses FalkorDB relationship-index
  syntax `CREATE INDEX FOR ()-[r:RelType]-() ON (r.id)`.
- **1 hot-path index** `:Node {graph_id}` for the persist-time check
  per ADR-0123 §2.

`FalkorClient.__init__` fires `bootstrap(self)` lazily (per P2 A) so
testers never see a "you forgot to bootstrap" error.

### Persist-time check (ADR-0123 §2)

After each UNWIND batch, `GraphRepository.persist` runs a single
indexed scan per label: `MATCH (n:Label) WHERE n.id IN $ids RETURN
n.id, count(n)`. Rows with `count > 1` raise
`IntegrityCheckError`. Cost is O(K log N) per batch on the index.

### Integrity scanner (ADR-0123 §3)

`verify_invariants(mg) -> IntegrityReport` walks the Metagraph
in-memory and emits 5 buckets:

1. `duplicate_ids` — same id under more than one element per label.
2. `cross_graph_edges` — `:Edge` rows with endpoints in different
   graphs (Edge is intra-graph by ADR; cross-graph linking is
   IntergraphEdge's job).
3. `orphan_hyperedges` — HyperEdges with zero members.
4. `orphan_metaedges` — MetaEdge / MetaHyperEdge referencing graphs
   not present.
5. `dangling_tombstones` — Phase 10 territory; empty in Phase 07.

Sibling `verify_invariants_graph(graph) -> PartialIntegrityReport`
runs the 3 graph-internal buckets (Phase 07 P98 A) and powers
`mindsos persistence verify --source=db --graph G` until Phase 08's
metagraph_loader unblocks the full scanner against FalkorDB.

### AsyncClient (ADR-0126)

`ThreadPoolAsyncClient` wraps a sync `Client` via `asyncio.to_thread`.
~50 LOC. Two gotchas documented in ADR-0126:

- **Thread-pool starvation** under high concurrency. Default asyncio
  pool is small (CPU count). Callers needing more parallelism should
  install a larger pool.
- **Cancellation is cosmetic.** `asyncio.CancelledError` propagates
  from `to_thread` but the underlying Cypher query keeps running.
  Documented as a known limitation; native async FalkorDB driver
  would fix this.

### OCC (ADR-0127)

Every persistable Core element + the 2 instance classes carry a
`_version: int = 1` field. `GraphRepository.update_*_properties`
always bumps `_version` on the update path (P7 C); OCC enforcement
is opt-in via the `expected_version` parameter:

```python
# Mechanism (L1): bump always, no OCC predicate.
new_version = repo.update_node_properties(graph_id, node_id, props)

# Mechanism + OCC predicate.
new_version = repo.update_node_properties(
    graph_id, node_id, props, expected_version=current_version,
)
# Zero-row MATCH ⇒ OptimisticConcurrencyConflict (stale write).
```

`MissingExpectedVersionError` is NOT at L1 (Phase 07 P84 B); the
Global-policy wrapper at L0/L2 raises it when callers omit
`expected_version` on Global writes. Phase 07 ships the mechanism;
L0/L2 ships the policy.

### `_props_json` encoding (ADR-0130 + P62 A)

Metagraph `.properties` dict is JSON-encoded onto a single
`_props_json` Cypher property on the `:Metagraph` anchor row using:

```python
json.dumps(properties, sort_keys=True, ensure_ascii=False,
           separators=(",", ":"))
```

Per Phase 07 P83 C — no size cap. The narrow chained driver-exception
catch in `MetagraphRepository.persist` maps oversized writes to
`PersistenceError`:

```python
try:
    client.run_query(anchor_query, params)
except (redis.exceptions.ResponseError,
        falkordb.exceptions.FalkorDBError) as e:
    raise PersistenceError(f"...") from e
```

Graph `.properties` writer is NOT shipped at Phase 07 (P9 C; deferred
per PHASE_MAP §7 Q4). When the writer ships (Phase 10 likely),
`build_create_graph_anchor` gains a `props_json` parameter additively.

### 4-step persist lifecycle (P96 A)

`MetagraphRepository.persist(mg)` orchestrates:

1. **Core writes** — anchor + contained graphs + MetaEdges +
   MetaHyperEdges + IntergraphEdges + IntergraphHyperEdges.
2. **WAL commit** — if a WAL context is in scope (mechanism-only at
   Phase 07; no L1 consumer).
3. **Observers fire** — `Metagraph._persist_observers` invoked.
   Phase 07 consumer:
   `mindsos_instances.persistence.InstanceRepository.persist_all`
   (subscribed via `mindsos_instances.attach_registry(mg)`).
4. **Return**.

Observer failure leaves Core+WAL state consistent; instance
persistence may be partial. Tester convention (P33 A): re-run
`persist` (MERGE-idempotent).

### Tombstones (P69 A)

Per-(graph, element) shape:
`(:Tombstone {graph_id, element_id, element_kind, removed_at, removed_by?})`.

Tombstone-write primitives ship in Phase 07 (P16-pre); the read-path
filter that excludes tombstoned elements lands in Phase 10
(soft-delete read-filter per ADR-0133).

## Single-Graph load (Phase 07 M14)

`mindsos_core.reconstruction.load_graph(client, graph_id)` returns a
reconstructed `Graph` with anchor + nodes + edges + hyperedges +
`_version` fields restored from FalkorDB. Streaming loader (ADR-0124)
and metagraph_loader land in Phase 08 (below).

## Reconstruction layer (Phase 08)

Phase 08 ships the FalkorDB → Python read surface. ADR-0124 flips
Accepted in Phase 08 (M3 A — flip-inline on consumer ship; acceptance
criterion per P27 C; impl-refs amended per RR-6 A; signature shrinks
per PB-3 A; `RefreshUnsafeError` enforcement deferred per PB-5 B).

The package `mindsos_core.reconstruction/` exposes six load-side
symbols + three re-exported exception classes (R4-12 A). See
[the API reference](../../api/core/loaders.md) for signatures + raise
paths.

### `load_graph` (Phase 07 surface preserved)

Phase 08 refactors the Phase 07 function internally to call
`iter_load_graph` with a full-load sentinel per RR-12 A
(`load_graph = drain(iter_load_graph(..., batch_size=_FULL))`).
Result is byte-equivalent to the prior Phase 07 implementation.

### `iter_load_graph` (NEW — RPB-1 A semantics)

```python
def iter_load_graph(client, graph_id, *, identity=None,
                    schema=None, batch_size=10_000) -> Iterator[Graph]:
    ...
```

Intermediate batches are **nodes-only**; the final batch trails any
edges + hyperedges over the cumulative node set. The yielded `Graph`
object identity is stable across yields (mutating in-place); the final
yield holds the full assembled graph. RPB-10 A — `IntergraphEdge` /
`IntergraphHyperEdge` are skipped (those load via `MetagraphLoader`).

### `MetagraphLoader` + `load_metagraph` (NEW)

Orchestrator class + module convenience function (PB-2 C hybrid).
The class is **orchestration-only** (RR-8 A) — sibling loaders
(InstanceLoader in Phase 08; XRefLoader in Phase 09 per RR-10 A)
subscribe via `Metagraph.register_after_load_observer`, never via a
sub-loader handle.

**Locked load sequence** (R4-1 A / R4-8 A / M12):

1. `recover(client, metagraph_id)` — first L1 WAL consumer (PB-6 B).
   Narrow-catches `WALReplayerMissingError` (RPB-3 C); other failures
   propagate as `PersistenceError`.
2. Anchor row + property bag + `schema_name` plain property (PB-11 A
   — name only; vocab content NOT auto-attached).
3. Contained graphs via `load_graph` (default) or `iter_load_graph`
   per-graph (`batch_size=int` per RR-2 D).
4. MetaEdges (untyped MATCH + `r.metagraph_id` filter).
5. MetaHyperEdges (`:MetaHyperEdge` node + `:MEMBER_GRAPH` rels).
6. IntergraphEdges (untyped MATCH + cross-graph guard).
7. IntergraphHyperEdges (`:ANCHOR` + `:MEMBER` rels — Phase 08 P61 A
   fix; see below).
8. `_dispatch_after_load(mg._after_load_observers, mg)` — single fire
   (RPB-9 A); per-observer exception isolation (RR-9 A — diverges
   from `_dispatch_after_persist` by design).

### WAL recover-on-load (PB-6 B — first L1 consumer)

`load_metagraph` ALWAYS calls `recover()` as step 0 of the locked
sequence. The narrow-catch on `WALReplayerMissingError` (RPB-3 C)
means Phase 08 loads with no registered replayers are silent no-ops;
once L0/L2 (Phase 18+) register replayers, the same call becomes
meaningful. Driver-level errors continue to propagate as
`PersistenceError`. `load_graph` does NOT call `recover()` (RPB-5 A
asymmetry — standalone Graph has no metagraph recovery context).

### Observer-driven instance load (RR-9 A + PB-4 A)

`Metagraph.register_after_load_observer(cb)` provides the
sibling-package extension slot (PB-4 A). `mindsos_instances.attach_registry(mg)`
subscribes an after-load observer that routes through
`mindsos_instances.reconstruction.InstanceLoader.load_into(mg)`.

The dispatcher `_dispatch_after_load` (in `mindsos_core/_observers.py`)
applies **per-observer exception isolation** (RR-9 A): a failing
observer is logged + swallowed; the originating load returns the
constructed Metagraph regardless. Diverges from
`_dispatch_after_persist` (Phase 07) which lets exceptions propagate;
locked rationale: a half-rehydrated sibling-package should not tear
down the entire load — partial-rehydration is operator-visible via
`verify`.

### `MetagraphLoader.refresh(mg, role)` (ADR-0124 §2)

Drops role-graphs via `mg.remove_graph(gid)` (RPB-2 A — fires Phase 06
remove-observer cascade for dependent instances); reloads via
`load_graph`; fires `after_load` to rehydrate instances.

* **Identity preservation** (R4-7 A+C) — `id(mg)` + `id(mg.identity)`
  unchanged; downstream `weakref.proxy(mg.identity)` continues to
  resolve.
* **Empty role** (R4-2 D) — log WARNING + no-op return.
* **Role mismatch** (R4-2 D) — raise `RoleMismatchError` with both
  roles surfaced.
* **`RefreshUnsafeError`** (PB-5 B) — class only; not raised in
  Phase 08. Per-role mutation-flag tracking deferred.

### Phase 08 P61 A — IntergraphHyperEdge anchor persist fix

Phase 07's `build_unwind_create_intergraph_hyperedges` persisted only
`:MEMBER` rels; `:ANCHOR` rels were absent. The
`IntergraphHyperEdge` dataclass invariant `n_anchors ≥ 1` made
round-trip impossible. Phase 08 P61 A additively extends the persist
builder + persist-row construction to write `:ANCHOR` rels alongside
`:MEMBER`. Phase 08's `MetagraphLoader._load_intergraph_hyperedges`
reads both rel kinds.

Old data persisted before the Phase 08 fix has no `:ANCHOR` rels —
affected rows surface in the loader's WARNING log + are SKIPPED.
Recovery: re-`sync --metagraph M --replace` under Phase 08 (after
dropping dependent state per RPB-4 C).

### Exception hierarchy additions (R4-3 A)

* `RefreshUnsafeError` ← `PersistenceError` (PB-5 B class only).
* `WALReplayerMissingError` ← `PersistenceError` (RPB-3 C narrow-catch
  sentinel).
* `RoleMismatchError` ← `PersistenceError` (R4-2 D refresh corruption
  signal).

No `ReconstructionError` umbrella class (R4-3 A — `PersistenceError`
suffices).
