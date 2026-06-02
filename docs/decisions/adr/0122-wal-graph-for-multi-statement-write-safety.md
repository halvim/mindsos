---
title: WAL graph for multi-statement write safety
status: Accepted
date: 2026-04-27
accepted_date: 2026-05-13
layer: L1
amends: [0007]
---

# ADR-0122: WAL graph for multi-statement write safety

**Status:** Accepted (Phase 07 — M3 A inline flip 2026-05-13)

**Date:** 2026-04-27 · **Accepted:** 2026-05-13

**Amends:** ADR-0007 (in-memory snapshot rollback — narrowed to release-ship by ADR-0118 + ADR-0129; the ordinary-multi-statement-rollback role moves to this ADR's WAL graph).

**Related:** ADR-0121 (substrate commitment), ADR-0023 (two-step writes — idempotent path), ADR-0118 (per-user transactional promotion uses this pattern).

## Context

FalkorDB processes Cypher statements one at a time. `run_batch` is a sequential pipeline; a failure on statement N of M leaves statements 1..N-1 committed and N+1..M unwritten. On-disk state is inconsistent with no driver-level rollback.

`MetagraphSnapshot` (ADR-0007 / ADR-0027) provides in-memory rollback but only protects the Python-side state — the FalkorDB side stays partial. The pivot's release-ship narrows snapshot to that single use case (ADR-0129). For ordinary multi-statement writes (KL `propose_for_promotion`, L3 capacity registration, every multi-graph write), we need a substrate-friendly rollback path.

## Decision

Two-piece hybrid:

### 1. Idempotent writes everywhere

Audit existing Cypher writes in `mindsos_core/persistence/` for MERGE-on-id pattern (the precedent set by ADR-0023). Fix any that aren't. Cheap pass. Most writes already match this shape.

Failure of an idempotent write at any point in a batch is replay-safe: re-running the batch from start produces the same end state.

### 2. WAL graph for promote and release-ship

Multi-statement operations that *touch multiple graphs* or *cannot be made idempotent* (e.g., delete operations, ref rewrites) write **intent records** to a sibling `:WAL` graph in the same Metagraph before applying.

```
Metagraph "alice"
├── Graph (role="lexicon")        ← user data
├── Graph (role="ontology")       ← user data
└── Graph (role="_wal")           ← write-ahead log; sibling graph
    ├── :WALEntry {operation_id, kind, payload, started_at, committed: bool}
    └── ...
```

**Lifecycle:**

1. **Write phase.** Caller opens a `WriteSet` (per ADR-0124's `WriteSet` primitive — companion ADR). Operations populate `:WALEntry` rows with `committed=false`.
2. **Apply phase.** WriteSet executes the actual writes against target graphs.
3. **Commit phase.** Each `:WALEntry` is stamped `committed=true` after its corresponding write succeeds.
4. **Crash recovery.** On server start, scan `:WAL` graphs for any `:WALEntry {committed: false}` rows. Replay the operation (idempotent) or compensate (delete operations have explicit compensators).
5. **GC.** A periodic CLI tool (`mindsos-server wal-gc`) deletes `:WALEntry` rows older than N days where `committed=true`. Manual; not a daemon thread in v1.

**Constraints:**

- WAL graph lives **as a sibling Graph in the same Metagraph** (shared identity registry; one persist round-trip; atomic commit for the metagraph as a whole). Not as a separate Metagraph.
- WAL is **per-Metagraph**, not global. Each user's Local has its own `_wal` graph; Global has one.
- WAL is **opt-in** at the WriteSet level. Reads do not pass through WAL. Single-statement writes that are already idempotent do not need WAL.
- WAL entries are **opaque to Core**. The replay/compensate logic lives at the calling layer (KL knows how to replay a `propose_for_promotion`; the server knows how to replay a `release_update`).

**Schema (the `:WALEntry` node):**

```
properties:
  operation_id   : string  (UUID; unique per operation)
  kind           : string  ("kl.propose_for_promotion", "server.release_update", ...)
  payload        : string  (JSON-encoded; operation-specific)
  started_at     : datetime
  committed      : bool    (false by default; flipped to true on success)
  committed_at   : datetime (null until committed)
  replayer_layer : string  ("knowledge", "server", "capacity"; tells reload who runs the replay)
```

**Replay registry:**

`mindsos_core` exposes a registry: `WAL.register_replayer(kind: str, replayer: Callable[[dict], None])`. KL registers its replayer for `kl.propose_for_promotion`; server registers for `server.release_update`. On crash recovery, Core reads each uncommitted `:WALEntry` and dispatches to the registered replayer.

## Rationale

The pivot narrows `MetagraphSnapshot` to release-ship rollback only (ADR-0129). KL's existing snapshot use disappears; KL needs another rollback story for `propose_for_promotion` (per ADR-0118). WAL graph is the natural substrate-friendly answer because:

- It uses Core primitives only — a sibling Graph with `:WALEntry` nodes. No new substrate concepts.
- It survives process crashes (rows persist in FalkorDB).
- It's transparent to non-WAL writes (single-statement writes pay nothing).
- It composes with the per-user-mutex contract — WAL entries for one user's Local are written and replayed under that user's lock.

The "idempotent everywhere" half handles the common case cheaply. WAL is reserved for the operations where idempotency is hard (deletes, multi-graph rewrites). Hybrid pays only for the cases that need it.

## Consequences

**Good:**

- KL `propose_for_promotion` can write to its Local + pending-Global atomically through WAL; on crash, replay or rollback is deterministic.
- Server `release_update` (ADR-0118) gains a substrate-level rollback for the canonical-Global swap that complements `MetagraphSnapshot`'s in-memory layer.
- L3 capacity-state writes that touch multiple capacity graphs can use WAL.
- The phantom-promotion bug (ADR-0118 §"Context", item 1) is structurally addressed at the FalkorDB level, not just the in-memory level.

**Tradeoffs:**

- Each protected operation pays one extra round-trip per WAL entry (write `:WALEntry` with `committed=false`, then write user data, then SET `committed=true`). For a 10-statement promote, that's 12 statements instead of 10. Bounded.
- WAL graph grows monotonically until GC runs. Manual GC means operators have to remember; v1 acceptable, may need daemon in v2.
- Replay registry (`WAL.register_replayer`) is a Core extension point that runs higher-layer code at recovery time. Each replayer must be carefully authored; a buggy replayer can corrupt state on crash recovery.
- WAL semantics are not free for callers: the WriteSet API (ADR-0124) is the ergonomic surface, but new writes that need protection must explicitly opt in.

**Coordinated changes:**

- `mindsos_core/persistence/wal.py` (new module) — WAL primitives, replayer registry.
- `mindsos_core/persistence/write_set.py` (new) — WriteSet integration with WAL.
- `mindsos_core/reconstruction/wal_recovery.py` (new) — crash-recovery scanner; called from `mindsos_server` boot path.
- KL: `propose_for_promotion` (per ADR-0118) writes through WAL.
- Server: `release_update` writes through WAL for the pending→canonical swap, in addition to `MetagraphSnapshot`.
- CLI: `mindsos-server wal-gc --older-than=7d` (and `wal-status` for inspection).

## Alternatives considered

1. **Idempotent writes only; no WAL.** Rejected — delete operations and ref rewrites are not idempotent under MERGE semantics; KL `propose_for_promotion` cannot be made fully replay-safe without WAL. The phantom-promotion bug stays.
2. **Saga + compensating transactions per operation.** Rejected — every operation needs a hand-written compensator; bug-prone; high implementation cost. WAL gets the same correctness with one shared mechanism.
3. **WAL as a separate FalkorDB graph (not sibling).** Rejected — violates one-Metagraph-one-IdentityRegistry; loses atomic-commit semantics with the user data; complicates per-user WAL lookup.
4. **Outbox pattern in SQLite (server.db).** Rejected — couples Core to SQLite; cross-store consistency between FalkorDB and SQLite for every write is the problem ADR-0114 already wrestles with at release-ship. Keeping WAL in FalkorDB keeps Core substrate-agnostic.
5. **Adopt Memgraph for transactional safety.** Rejected — see ADR-0121.

## Implementation references

- New: `mindsos_core/persistence/wal.py`, `write_set.py`, `wal_recovery.py`.
- Coordinated: KL `propose_for_promotion`, server `release_update`, server boot path.
- CLI: `mindsos-server wal-gc`, `mindsos-server wal-status`.
- Tests: `tests/unit/core/test_wal.py` + integration test that crashes mid-promote and verifies recovery.

**Acceptance criteria (Phase 07 P27 C amendment):** *Accepted when L1 mechanism ships + `docs/dev/internals/core.md` documents the pattern; consumer integration (KL `propose_for_promotion`, server `release_update`) tracked separately.* Met by Phase 07: `WriteAheadLog` + `recover()` + `register_replayer()` ship in `mindsos_core/persistence/wal.py`; primary context-manager API `with wal.entry(...)` per P50 B; `docs/dev/internals/core.md` "Persistence layer" §WAL documents the pattern.
