---
title: Streaming loader — iter_load_graph and MetagraphLoader.refresh
status: Accepted
date: 2026-04-27
accepted_date: 2026-05-14
accepted_in_phase: 08
layer: L1
---

# ADR-0124: Streaming loader — `iter_load_graph` and `MetagraphLoader.refresh`

**Status:** Accepted (Phase 08 — 2026-05-14)

**Date:** 2026-04-27 (proposed) → 2026-05-14 (accepted)

**Acceptance criterion (P27 C wording inherited from Phase 07 M3 A precedent):**
Accepted when L1 mechanism ships + `core.md` documents it; consumer
integration tracked separately.

**Phase 08 ship status:** Both methods land in
`halvim_mindsos/mindsos_core/reconstruction/{graph_loader.py,metagraph_loader.py}`
and `halvim_mindsos/docs/usage/core/persistence.md` /
`halvim_mindsos/docs/dev/internals/core.md` document them. Consumer
integration (L4 release-migration via `refresh(mg, role=ROLE_LEXICON)`,
KL bootstrap via `iter_load_graph`) tracked separately per the
acceptance-criterion wording.

**Related:** ADR-0030 (Client protocol), ADR-0118 (per-user transactional promotion — release migration walks Locals; benefits from per-role refresh).

## Context

`GraphLoader.load()` reads all nodes, edges, hyperedges in full. OEWN at scale is ~120k synsets + senses + lemmas; FrameNet adds ~10k frames + frame elements; cumulative Global metagraph at v1 is ~500k–1M nodes. Loading as a single Cypher result set blows memory at the Python side.

L4 design's release-model integration (per ADR-0118 §3) requires "delta reload" semantics: when a release ships, L4 needs cheap update to its in-memory metagraph without paying for a full reload. The current `MetagraphLoader.load(metagraph_id)` is always a full reload.

## Decision

Two additions to the loader API:

### 1. `iter_load_graph(client, graph_id, *, identity=None, batch_size=10_000)` (Phase 08 PB-3 A amendment)

**Phase 08 PB-3 A signature reduction.** The original ADR signature
included a redundant `metagraph_id` slot — shared-registry concerns
are the caller's responsibility via the `identity=` kwarg. Phase 08
ships the graph-scoped form as a **function** (not a method on a class):

```python
def iter_load_graph(
    client: Client,
    graph_id: str,
    *,
    identity: IdentityRegistry | None = None,
    schema: Any = None,
    batch_size: int = 10_000,
) -> Iterator[Graph]:
    """Yield partial Graph objects sized by ``batch_size``.

    Intermediate yields are nodes-only (per Phase 08 RPB-1 A); the
    final yield trails any deferred cross-batch edges + hyperedges
    over the cumulative node set. Cross-graph primitives
    (IntergraphEdge / IntergraphHyperEdge) are skipped (RPB-10 A) —
    they load via :meth:`MetagraphLoader.load` only.
    """
```

**Phase 08 semantics (RPB-1 A + RPB-10 A locks):**

- **Intermediate batches are nodes-only.** Each intermediate yield
  carries a partial `Graph` with up to `batch_size` nodes (id-ordered);
  no edges, no hyperedges.
- **Final batch trails the deferred edges + hyperedges.** After the
  last node-page, one more yield carries all edges + hyperedges whose
  endpoints are present in the cumulative node set. This makes cross-
  batch edges (e.g., node-3 → node-23 under `batch_size=10`)
  recoverable without duplicate emit cost.
- **Yielded `Graph` object identity is stable across yields** (caller
  observes the same in-flight object growing); the final yield is the
  fully-assembled graph.
- **The iterator is stable under concurrent writes** via FalkorDB
  snapshot isolation (unchanged from the original proposal).
- **`load_graph(client, gid)` is a thin wrapper of
  `drain(iter_load_graph(client, gid, batch_size=_FULL_LOAD_SENTINEL))`**
  per RR-12 A. Backwards-compatible — same Cypher; same id-ordering;
  result byte-equivalent to the prior Phase 07 implementation.
- **Intra-graph only** (RPB-10 A). IntergraphEdge / IntergraphHyperEdge
  load via `MetagraphLoader.load` (R4-1 A locked sequence).

**Implementation:**

Cypher-level pagination via `ORDER BY n.id SKIP $offset LIMIT $limit`
against the `:Node {graph_id}` hot-path index (Phase 07 P95 B).

### 2. `MetagraphLoader.refresh(mg, role, *, schema=None)`

```python
def refresh(
    self,
    mg: Metagraph,
    role: str,
    *,
    schema: Schema | None = None,
) -> None:
    """Reload the role-graph(s) with role=`role` in `mg`. Replaces in place;
    existing Graph objects with that role are detached, and fresh Graphs
    are loaded from FalkorDB and attached. The Metagraph object identity
    is preserved (matches MetagraphSnapshot semantics, ADR-0027).
    """
```

**Semantics:**

- **Replace, not merge.** The role-graph(s) being refreshed are fully reloaded; any in-memory mutations since last load are discarded.
- **Identity preservation.** `id(mg)`, `id(mg.identity_registry)` are unchanged. Existing references held by other layers (KL `installed_locals`, L3/L4 cached views) survive.
- **Atomic per-role.** All graphs with `role=$role` swap together; never partially refreshed.
- **Triggered by release model.** L4 calls `refresh(mg, role=ROLE_LEXICON)` after detecting a release with rewrites in that role. Per-role granularity matches the release manifest's role-graph-level shipping.
- **Returns nothing.** Mutates in place. Caller checks the new Graph state via `mg.graphs_by_role(role)`.

**Constraint (Phase 08 PB-5 B amendment — class shipped; enforcement deferred):**

`refresh` is conceptually invalid for roles whose graphs hold
uncommitted in-memory changes. Phase 08 ships the
`RefreshUnsafeError` class only — per-role mutation-flag tracking +
enforcement are deferred to a later phase. Callers using `refresh`
after in-memory mutations LOSE those mutations silently in Phase 08.
Documented loudly in `docs/usage/core/persistence.md`.

### Out-of-scope (deferred)

**`LazyGraph` proxy.** A graph that fetches nodes-on-access from FalkorDB with LRU cache. Trigger: first scaling incident where iter_load + refresh aren't enough. Tracked in `docs/changelog/roadmap.md` under "L1 future implementation."

**Reason for deferral:** `LazyGraph` is ~500 LOC, complicates debugging ("why is this slow?"), and has cache-invalidation semantics that need real-world data to design correctly. iter_load + refresh cover the realistic v1 workload (one-shot import, delta reload).

## Rationale

The two pieces solve different problems:

- **`iter_load`** addresses the memory ceiling: a 1M-node import OOMs on full-load; with batch_size=10K, peak memory is bounded.
- **`refresh`** addresses delta-reload cost: L4 holds long-lived in-memory metagraphs; without per-role refresh, each release ship triggers a full metagraph reload, which is wasteful when most roles haven't changed.

Both use the existing FalkorDB Cypher pagination (`SKIP/LIMIT`) and the ADR-0123 indexes on `n.id`. No new substrate features required.

The deferred `LazyGraph` is the third option but pays for flexibility no current consumer needs. Defer until first scaling incident.

## Consequences

**Good:**

- L4 release integration (per ADR-0118) gains an efficient delta-reload path.
- KL bootstrap can stream-load on startup for huge knowledge bases (DOLCE + OEWN + FrameNet at full size).
- L3 capacity discovery iterates in bounded memory (`iter_load` + filter for capacity-typed nodes).
- The pivot's migration job (per `mindsos_server/migration.py`) walks user Locals via `iter_load` to apply rewrite-maps without OOMing.
- Tests can construct large fixture metagraphs via `iter_load` in CI without burning RAM.

**Tradeoffs:**

- Pagination via `SKIP/LIMIT` has a known O(N) cost on the SKIP itself for large N. Mitigation: index on `id` makes the per-batch cost O(K log N); the full-iteration cost is O(N log N) instead of O(N) without index. Acceptable.
- `refresh` discards in-memory mutations. Callers that hold uncommitted state must persist first. Surfacing via `RefreshUnsafeError` is mandatory.
- Cross-batch reference resolution complicates client-side merge logic. Callers using `iter_load` for assembly (rather than ad-hoc inspection) need to know the IdentityRegistry handles this; documented in the user guide.

**Coordinated changes:**

- `mindsos_core/reconstruction/graph_loader.py` — new `iter_load` method.
- `mindsos_core/reconstruction/metagraph_loader.py` — new `refresh` method.
- `mindsos_core/models/metagraph.py` — track per-role mutation flag for `RefreshUnsafeError` detection.
- L4 release-integration code (post-pivot v1) — uses `refresh` after migration applies.

## Alternatives considered

1. **Status quo (full load only).** Rejected — first big import OOMs; L4 cannot do delta reloads efficiently.
2. **`LazyGraph` proxy as the primary mechanism.** Rejected for v1 — see "Out-of-scope" above. Complexity outweighs benefit for now; ship iter_load + refresh first; revisit if real workloads expose the gap.
3. **Streaming Cypher via cursor.** Considered. FalkorDB driver may support cursor-based streaming; pagination via `SKIP/LIMIT` is the portable fallback. Implementer can opt for cursor if available.
4. **`refresh` as merge instead of replace.** Rejected — merge requires conflict resolution semantics for nodes that exist on both sides with different properties. Replace is unambiguous; uncommitted changes must be flushed first or accepted-as-lost.

## Implementation references (Phase 08 RR-6 A — actual paths in `halvim_mindsos/`)

* `mindsos_core/reconstruction/graph_loader.py::iter_load_graph` — graph-scoped streaming function (PB-3 A signature).
* `mindsos_core/reconstruction/graph_loader.py::load_graph` — Phase 07 surface; refactored internally to call `iter_load_graph(..., batch_size=_FULL_LOAD_SENTINEL)` per RR-12 A.
* `mindsos_core/reconstruction/metagraph_loader.py::MetagraphLoader` — orchestrator class (RR-8 A; minimal `(client)` constructor per R4-11 A).
* `mindsos_core/reconstruction/metagraph_loader.py::MetagraphLoader.load` — locked R4-1 A read sequence (recover → anchor → graphs → meta-edges → meta-hyperedges → intergraph-edges → intergraph-hyperedges → `after_load` fire).
* `mindsos_core/reconstruction/metagraph_loader.py::MetagraphLoader.refresh` — `refresh(mg, role, *, schema)` per RPB-2 A / R4-2 D / R4-7 A+C.
* `mindsos_core/reconstruction/metagraph_loader.py::load_metagraph` — module convenience function (RR-5 B) wrapping `MetagraphLoader(client).load(...)`.
* `mindsos_core/_observers.py::AfterLoadCallback` + `_dispatch_after_load` — per-observer exception isolation (RR-9 A diverges from `_dispatch_after_persist`).
* `mindsos_core/models/metagraph.py::Metagraph.register_after_load_observer` — observer plumbing entry point (PB-4 A).
* `mindsos_core/exceptions.py::RefreshUnsafeError` / `WALReplayerMissingError` / `RoleMismatchError` — 3 new exception classes (R4-3 A).
* `mindsos_instances/reconstruction/instance_loader.py::InstanceLoader` — observer-driven sibling-side rehydration subscriber (PB-4 A; subscribed via `mindsos_instances.attach_registry` per Phase 06 P49 B helper).
* `mindsos_cli/commands/persistence.py` — CLI extensions: `sync --metagraph M [--replace]` (PB-8 A + RPB-4 C); `load --metagraph M [--to-json] [--json]` (PB-9 A + R4-5 A + RR-7 A); `verify --source=db --metagraph M` UNBLOCK (PB-7 A); `--graph G | --metagraph M` mutex (R4-6 A).
* `docs/usage/core/persistence.md` — usage examples + recipes for the new verbs + RefreshUnsafeError constraint + recover-on-load.
* `docs/dev/internals/core.md` — NEW "Reconstruction layer" section (RR-15 A).
* `docs/api/core/loaders.md` — full API reference (NEW per RR-15 A).
* Tests: `tests/phase_08/` — exercise the load surface (unit via InMemoryClient call-recording per RPB-13 B; integration via `@pytest.mark.integration` against a live FalkorDB sidecar per the locked test methodology).
