---
last_confirmed_phase: 08
---

# Core Loaders — `mindsos_core.reconstruction`

Phase 08 ships the FalkorDB → Python reconstruction surface. The
package exposes six load-side symbols + three reconstruction-side
exception classes (R4-12 A).

## `load_graph`

```python
def load_graph(
    client: Client,
    graph_id: str,
    *,
    identity: Optional[IdentityRegistry] = None,
    schema: Any = None,
) -> Graph
```

Reconstructs the `Graph` with `graph_id`. Phase 07 surface preserved;
Phase 08 refactors internally to call `iter_load_graph` with a
single-batch sentinel per RR-12 A (ADR-0124 "load() becomes a thin
wrapper of `list(iter_load(...))`" claim). The result is byte-equivalent
to the prior Phase 07 implementation.

**Args:**

* `client` — connected `Client` (e.g. `FalkorClient`).
* `graph_id` — Cypher `:Graph.id` to load.
* `identity` — optional shared `IdentityRegistry`. When `None`, a fresh
  registry is created and `graph_id` is registered. When passed in by
  `MetagraphLoader.load`, every element id registers under the shared
  registry (preserves ADR-0020 metagraph-wide unique-id invariant).
* `schema` — optional schema; Phase 08 accepts as no-op kwarg (R4-4 B
  forward-compat parity).

**Raises:**

* `PersistenceError` — no `:Graph` row with `id=graph_id`, or any
  sub-query driver failure.

## `iter_load_graph`

```python
def iter_load_graph(
    client: Client,
    graph_id: str,
    *,
    identity: Optional[IdentityRegistry] = None,
    schema: Any = None,
    batch_size: int = 10_000,
) -> Iterator[Graph]
```

Memory-bounded streaming variant (ADR-0124 + PB-3 A signature).
**Intermediate batches are nodes-only** (RPB-1 A); the **final batch
trails** any deferred cross-batch edges + hyperedges over the
cumulative node set. The yielded `Graph` object identity is stable
across yields (every yield returns the same in-flight graph with more
nodes attached); the final yield's `len(g.nodes)` equals
`sum_of_batch_node_counts`.

**Locked semantics:**

* `batch_size: int >= 1` required; `batch_size <= 0` raises
  `ValueError`.
* Cross-graph primitives skipped (RPB-10 A) — `IntergraphEdge` /
  `IntergraphHyperEdge` load via `MetagraphLoader.load` only.
* Stable pagination via `ORDER BY n.id SKIP $offset LIMIT $limit`
  against the `:Node {graph_id}` hot-path index (Phase 07 P95 B).

**Args:** same as `load_graph` plus `batch_size: int`.

**Yields:** partial `Graph` instances. The final yield holds the full
assembled graph.

**Raises:** `PersistenceError` on anchor / sub-query failure;
`ValueError` on invalid `batch_size`.

## `class MetagraphLoader`

```python
class MetagraphLoader:
    def __init__(self, client: Client) -> None: ...
    def load(
        self,
        metagraph_id: str,
        *,
        batch_size: Optional[int] = None,
        identity: Optional[IdentityRegistry] = None,
        schema: Any = None,
    ) -> Metagraph: ...
    def refresh(
        self,
        mg: Metagraph,
        role: str,
        *,
        schema: Any = None,
    ) -> None: ...
```

Phase 08 orchestrator (RR-8 A — no sub-loader handles; siblings
subscribe via `register_after_load_observer`). Minimal constructor
(R4-11 A — `client` only); all other kwargs are per-call.

### `MetagraphLoader.load(metagraph_id, *, batch_size, identity, schema)`

Locked R4-1 A / R4-8 A read sequence:

1. `recover(client, metagraph_id)` — first L1 WAL consumer (PB-6 B).
   Narrow-catches `WALReplayerMissingError` (RPB-3 C) → silent no-op
   when no replayer is registered. Other failures propagate as
   `PersistenceError`.
2. Anchor row read (decodes `_props_json`; restores `mg.schema_name`
   plain property per PB-11 A).
3. Contained Graph reads via `load_graph` (default; `batch_size=None`)
   or `iter_load_graph` per-graph (`batch_size: int` — RR-2 D).
4. MetaEdges (untyped `MATCH (s:Graph)-[r]->(t:Graph) WHERE
   r.metagraph_id = $mid`).
5. MetaHyperEdges (`:MetaHyperEdge` node + `:MEMBER_GRAPH` rels).
6. IntergraphEdges (`MATCH (s:Node)-[e]->(t:Node) WHERE
   e.metagraph_id = $mid AND s.graph_id <> t.graph_id`).
7. IntergraphHyperEdges (`:IntergraphHyperEdge` node + `:ANCHOR` +
   `:MEMBER` rels — both per Phase 08 P61 A fix).
8. `_dispatch_after_load(mg._after_load_observers, mg)` — single fire
   (RPB-9 A); per-observer exception isolation (RR-9 A).

**Returns:** reconstructed `Metagraph`. If
`mindsos_instances.attach_registry(mg)` was called BEFORE the load,
sibling-package instance state is rehydrated via the after-load
observer.

**Raises:** `PersistenceError` on anchor / sub-read failure.

### `MetagraphLoader.refresh(mg, role, *, schema)`

Reloads role-graph(s) of `role` in `mg` in place (RPB-2 A — proper
`mg.remove_graph(gid)` API; Phase 06 remove-observer cascade fires
for dependent instances; then loads new graphs and fires `after_load`).

**Identity preservation** (R4-7 A+C): `id(mg)` and `id(mg.identity)`
survive; external `weakref.proxy(mg.identity)` continues to resolve.

**Edge cases** (R4-2 D):

* Empty role: WARNING log + no-op return.
* Role mismatch (DB role drift): raises `RoleMismatchError` with
  `graph_id`, `in_memory_role`, `db_role` surfaced.

## `load_metagraph`

```python
def load_metagraph(
    client: Client,
    metagraph_id: str,
    *,
    batch_size: Optional[int] = None,
    identity: Optional[IdentityRegistry] = None,
    schema: Any = None,
) -> Metagraph
```

Module-level convenience function (RR-5 B) — thin wrapper of
`MetagraphLoader(client).load(metagraph_id, ...)`. Symmetric with
Phase 07's `load_graph` function-style surface.

## Exception classes (R4-3 A)

Three new classes ship in `mindsos_core.exceptions` and are re-exported
from `mindsos_core.reconstruction` for caller convenience (R4-12 A).
All inherit from `PersistenceError`.

### `RefreshUnsafeError`

PB-5 B — Phase 08 ships the **class only**; per-role mutation-flag
tracking + enforcement is deferred. Callers using
`MetagraphLoader.refresh` AFTER in-memory mutations LOSE those
mutations silently in Phase 08. ADR-0124 §Constraint amends to
"class shipped; enforcement deferred."

### `WALReplayerMissingError`

RPB-3 C — raised internally by `mindsos_core.persistence.wal.recover`
when an uncommitted `:WALEntry` row carries a `kind` that has no
registered replayer. `MetagraphLoader.load` narrow-catches this
sentinel on its initial `recover()` call (silent no-op so Phase 08
loads with no registered replayers don't fail).

### `RoleMismatchError`

R4-2 D — raised by `MetagraphLoader.refresh` when the in-memory
`mg.graphs[gid].role` differs from the persisted `:Graph.role` for
the same id. Indicates substrate corruption (external write race or
manual DB edit) rather than a user-recoverable error. Carries
`graph_id`, `in_memory_role`, `db_role` attributes for diagnostic
display.

## Cross-references

* [ADR-0124](../../decisions/adr/0124-streaming-loader-iter-load-and-refresh.md)
  — streaming loader + refresh. Accepted in Phase 08.
* [Persistence CLI usage](../../usage/core/persistence.md) — operator
  surface (`sync --metagraph M` / `load --metagraph M` /
  `verify --source=db --metagraph M`).
* [Persistence layer internals](../../dev/internals/core.md#reconstruction-layer-phase-08)
  — read-side mechanics in narrative form.
