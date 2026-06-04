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

### 1. `MetagraphDump` — backend-neutral serialization

`MetagraphDump` is a dedicated serialization dataclass that mirrors Metagraph structure (graphs, roles, nodes, edges, hyperedges, metaedges, metahyperedges, identity, schema) rather than reusing the live `MetagraphLoader` reconstruction path. It serializes to a **versioned envelope** `{"dump_schema_version": <int>, "payload": {...}}`; v1 payload is JSON, with msgpack reserved for a v2 envelope bump.

The dump is **backend-neutral**: the identical serialized form round-trips through both the FalkorDB-graph store and the SQLite-blob store. Every node carries its version pin as an `(iri, version_int)` pair — this is forced, not optional: under the D'1 retention model (ADR-0161, Chat B §4.4) a HEAD-only dump would silently break version-pinned side-by-side reads after a restore.

### 2. `FalkorDBLocalPersister`

Thin wrapper over the existing FalkorDB adapter. `save` reconstructs the user's role graphs (`local_<slug(user_id)>_<role>` per ADR-0004) from the dump using idempotent `MERGE`-on-id writes (ADR-0122) — no WAL graph, because a single-Metagraph replace is not a multi-graph operation. `delete` is best-effort (`delete_graph` with a `MATCH (n) DETACH DELETE n` fallback) and idempotent, returning `bool` per ADR-0011 §amendment-2 clause 2. Because Falkor delete-then-recreate is non-atomic under the single-process multi-threaded model (ADR-0009 / D32), `save` and `delete` acquire the per-user mutex from the `UserMutexRegistry` (ADR-0006) for the duration of the write.

### 3. `SQLiteLocalPersister`

Stores the serialized `MetagraphDump` as an **opaque blob** in a dedicated `locals.db` SQLite file — NOT in `server.db` (which ADR-0004 reserves for auth/sessions/audit). Table: `local_dumps(user_id TEXT PRIMARY KEY, dump BLOB NOT NULL, dump_schema_version INTEGER NOT NULL, updated_at TEXT NOT NULL)`. `save` is an `UPSERT`; `delete` is `DELETE` returning whether a row existed. This is the local-first / portable backing store; it stores a serialized dump, not graph-relational data, so it does not reintroduce the "graph gymnastics in SQLite" that ADR-0004 §Alternatives rejected (see ADR-0004 §amendment-2).

## Rationale

- **Dedicated dump dataclass over loader reuse.** An explicit serialization boundary is forward-versionable and unit-testable without standing up FalkorDB; coupling the on-disk format to loader internals would make every loader refactor a persistence-format migration.
- **Version pin in the dump is load-bearing, not belt-and-suspenders.** D'1 retention reads historical versions; a restore that dropped version pins would corrupt side-by-side history invisibly.
- **Two stores, one format.** A backend-neutral dump is the only way both persisters can share a single round-trip test surface and stay interchangeable behind the Protocol.
- **Mutex on write.** The single-process multi-threaded concurrency model still races on a non-atomic delete-then-recreate; the existing per-user mutex closes the window without a new locking primitive.

## Consequences

- A second SQLite file (`locals.db`) joins `server.db` and `version_db/`; the developer guide's backup story gains one cadence.
- `MetagraphDump` becomes a stable serialization contract; changing the payload shape requires a `dump_schema_version` bump and a read-path that tolerates the prior version.
- The persister is still configured once at `MindsOSServer` construction (ADR-0011 §amendment-3) and held for the process lifetime.

## Alternatives considered

1. **JSON over the live `MetagraphLoader` reconstruction schema.** Rejected — couples the on-disk format to loader internals.
2. **Falkor-native Cypher `CREATE` script replayed for both backends.** Rejected — forces the SQLite path to carry a Cypher interpreter; not backend-neutral.
3. **Single backing store (Falkor only) for v1.** Rejected at CR-2 — the SQLite-blob store is the local-first deployment path and costs little once the dump format is backend-neutral.
4. **Store the dump blob in `server.db`.** Rejected — violates the ADR-0004 concern split and entangles the user-data backup cadence with the auth/audit one.
