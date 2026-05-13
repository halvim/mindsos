---
last_confirmed_phase: 07
---

# Core layer internals — Persistence (Phase 07)

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
- [ADR-0130](../../decisions/adr/0130-property-bag-on-metagraph-graph.md) — `_props_json` encoding.

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
and metagraph_loader (ADR-0125) defer to Phase 08.
