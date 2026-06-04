---
title: L0 Local persister implementations + MetagraphDump serialization
status: Accepted
date: 2026-06-04
accepted_date: 2026-06-04
layer: L0
amends: [0011]
related: [0011, 0004, 0121, 0122, 0006, 0161]
---

# ADR-0160: L0 Local persister implementations + `MetagraphDump` serialization

**Status:** Accepted

**Date:** 2026-06-04

**Related:** ADR-0011 (LocalPersister protocol — this ADR ships the deferred impls), ADR-0004 (split persistence — see §amendment-2 SQLite-blob clarification), ADR-0121 (substrate commitment), ADR-0122 (WAL + idempotent writes), ADR-0006 (UserMutexRegistry), ADR-0161 (KL version surface — co-shipped).

## Context

ADR-0011 §amendment-2 clause 1 shipped the `LocalPersister` Protocol with an in-memory implementation only, and explicitly deferred `MetagraphDump` serialization plus the `FalkorDBLocalPersister` and `SQLiteLocalPersister` backing-store implementations to "the first phase that ships a backing-store persister." Phase 44 (Rail C, L0 substrate) is that phase. The Phase 44 governance ruling (CR-2, 2026-06-04) is to ship **both** backing stores, not one.

Designing the dump format before a real persistence boundary existed was judged speculative at Phase 25; that boundary now exists, so the serialization shape is settled here against two concrete consumers (a FalkorDB-graph store and a SQLite-blob store).

## Decision

### 1. `MetagraphDump` — `SQLiteLocalPersister`-internal serialization (reuses the promoted core state-file serializer)

`MetagraphDump` is NOT a Protocol-level type and is NOT backend-neutral. It is the **internal serialization of `SQLiteLocalPersister` only** (the Falkor persister round-trips natively — §2). The dump wraps the project's existing authoritative state-file JSON in a versioned envelope `{"dump_schema_version": <int>, "payload": {...}}`, where `payload` is the per-graph (state-file v=5) + metagraph (v=1) JSON produced by the state-file serializer **promoted from `mindsos_cli` into `mindsos_core` at this phase** (`graph_to_state` / `state_to_graph` / `metagraph_to_state` / `state_to_metagraph`; `mindsos_cli` keeps thin re-exports so layering holds and there is one authoritative serializer). v1 payload is JSON; msgpack is reserved for a v2 envelope bump.

Reusing the authoritative serializer rather than a net-new dataclass means the SQLite path cannot silently drift from the format the rest of the system reads, and it rides the existing migration chains. Each element preserves its `_version` OCC counter (already carried by the state-file format). Phase-11 side-by-side historical versions are a KL concern surfaced via `kl.read_at_version` (ADR-0161), not materialized in a Local dump.

### 2. `FalkorDBLocalPersister` — native, no dump

The Falkor persister does NOT serialize to `MetagraphDump`. It round-trips the Local natively through existing core machinery: `save` calls `MetagraphRepository.persist(metagraph)` (idempotent `MERGE`-on-id writes per ADR-0122; the `local_<slug(user_id)>_<role>` graph layout per ADR-0004); `load` reconstructs via `MetagraphLoader.load` (the same reconstruction the Falkor-backed L3 bootstrap uses). `delete` is best-effort (`delete_graph` with a `MATCH (n) DETACH DELETE n` fallback), idempotent, returning `bool` per ADR-0011 §amendment-2 clause 2. Because Falkor delete-then-recreate is non-atomic under the single-process multi-threaded model (ADR-0009 / D32), `save` and `delete` hold the per-user `UserMutexRegistry` mutex (ADR-0006) for the write.

### 3. `SQLiteLocalPersister`

Stores the serialized `MetagraphDump` (produced via the promoted core state-file serializer, §1) as an **opaque blob** in a dedicated `locals.db` SQLite file — NOT in `server.db` (which ADR-0004 reserves for auth/sessions/audit). Table: `local_dumps(user_id TEXT PRIMARY KEY, dump BLOB NOT NULL, dump_schema_version INTEGER NOT NULL, updated_at TEXT NOT NULL)`. `save` is an `UPSERT`; `delete` is `DELETE` returning whether a row existed. This is the local-first / portable backing store; it stores a serialized dump, not graph-relational data, so it does not reintroduce the "graph gymnastics in SQLite" that ADR-0004 §Alternatives rejected (see ADR-0004 §amendment-2).

## Rationale

- **Dedicated dump dataclass over loader reuse.** An explicit serialization boundary is forward-versionable and unit-testable without standing up FalkorDB; coupling the on-disk format to loader internals would make every loader refactor a persistence-format migration.
- **Version pin in the dump is load-bearing, not belt-and-suspenders.** D'1 retention reads historical versions; a restore that dropped version pins would corrupt side-by-side history invisibly.
- **Two stores, one format.** A backend-neutral dump is the only way both persisters can share a single round-trip test surface and stay interchangeable behind the Protocol.
- **Mutex on write.** The single-process multi-threaded concurrency model still races on a non-atomic delete-then-recreate; the existing per-user mutex closes the window without a new locking primitive.

## Consequences

- A second SQLite file (`locals.db`) joins `server.db` and `version_db/`; the developer guide's backup story gains one cadence.
- `MetagraphDump` becomes a stable serialization contract; changing the payload shape requires a `dump_schema_version` bump and a read-path that tolerates the prior version.
- The `LocalPersister` Protocol trafficks in live `Metagraph` (ADR-0011 §amendment-2 shape, retained — see ADR-0011 §amendment-3 clause 1); `MetagraphDump` is internal to `SQLiteLocalPersister`, not a Protocol type. The Falkor persister has no dump at all.
- The state-file serializer is promoted from `mindsos_cli` to `mindsos_core`; `mindsos_cli` re-imports it. One authoritative serializer now serves the CLI verbs and the SQLite persister.
- The persister is still configured once at `MindsOSServer` construction (ADR-0011 §amendment-3) and held for the process lifetime.

## Alternatives considered

1. **Net-new dedicated `MetagraphDump` dataclass** (the original Phase 44 S1 pick). Rejected on PR1.2 investigation — duplicates the authoritative `mindsos_cli` state-file serializer, risking silent format drift on the SQLite path. Promoting that serializer to core and reusing it (this ADR) avoids the duplication.
2. **Backend-neutral Protocol-level dump that both stores round-trip.** Rejected — the Falkor store round-trips natively via `MetagraphRepository.persist` / `MetagraphLoader.load`, so a Protocol-level dump only burdens the Falkor path; `MetagraphDump` is SQLite-internal instead.
3. **Single backing store (Falkor only) for v1.** Considered at CR-2; rejected — the SQLite store is the local-first deployment path and is cheap once the serializer is core-resident.
4. **Store the dump blob in `server.db`.** Rejected — violates the ADR-0004 concern split and entangles the user-data backup cadence with the auth/audit one.
