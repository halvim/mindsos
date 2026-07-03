---
title: L0 FalkorDBLocalPersister (native); SQLite + MetagraphDump deferred
status: Accepted
date: 2026-06-04
accepted_date: 2026-06-04
layer: L0
amends: [0011]
related: [0011, 0004, 0121, 0122, 0006, 0161]
---

# ADR-0160: L0 `FalkorDBLocalPersister` (native round-trip); SQLite + `MetagraphDump` deferred

**Status:** Accepted

**Date:** 2026-06-04

**Related:** ADR-0011 (LocalPersister protocol — this ADR ships the deferred Falkor impl), ADR-0004 (split persistence), ADR-0121 (substrate), ADR-0122 (WAL + idempotent writes), ADR-0006 (UserMutexRegistry), ADR-0161 (KL version surface — co-shipped).

## Context

ADR-0011 §amendment-2 clause 3 shipped the `LocalPersister` Protocol with an in-memory implementation only, deferring the `FalkorDBLocalPersister` and `SQLiteLocalPersister` backing stores to "the first phase that ships a user-Local-write surface." Phase 44 (Rail C, L0 substrate) is that phase.

CR-2 (2026-06-04) initially ruled "ship both backing stores." PR1.2 grounding reversed that ruling. Two findings drove the reversal:

1. **The project's authoritative Metagraph↔JSON serializer is multi-file, disk-coupled.** It lives in `mindsos_cli` and reconstructs a Metagraph by reading each contained graph and schema from its *own* on-disk state file (`_state_to_metagraph` → `state_mod.load_graph_state(gname)` per graph; `_state_to_graph` → `_load_schema_or_die` per schema, with `typer.Exit`). A single self-contained SQLite blob would require dependency-injecting those disk resolvers and composing an inline envelope — a real refactor that also touches the CLI's working reconstruct path (regression surface).
2. **`SQLiteLocalPersister` has no named v1 consumer.** It is the local-first / portable-export backing store; nothing in the v1 product writes or reads it.

Shipping a risk-bearing serializer refactor for a store with no consumer violates the project's "ship only what has a live consumer" discipline. The Falkor store, by contrast, has a real consumer (login hydrate / logout flush) and needs **no serialization at all**.

## Decision

### 1. `FalkorDBLocalPersister` — native, no dump

Ships now. It round-trips the Local natively through existing core machinery — no JSON serialization:

* `save(user_id, metagraph)` → `MetagraphRepository.persist(metagraph)` (idempotent `MERGE`-on-id writes per ADR-0122; `local_<slug(user_id)>_<role>` graph layout per ADR-0004).
* `load(user_id)` → reconstruct via `MetagraphLoader.load` (the same reconstruction the Falkor-backed L3 bootstrap uses).
* `delete(user_id) -> bool` → **scoped teardown keyed on the Local's `metagraph_id`**, idempotent (no such Metagraph → `False`) per ADR-0011 §amendment-2 clause 2.

**Substrate contract (settled here, was L0_SUBSTRATE_CHAT scope):** all Metagraphs — Global, pending, canonical, and *every* user Local — coexist in the one shared FalkorDB graph (`config.graph`), scoped by `metagraph_id`/name (`mindsos_server/persistence/bootstrap.py`). A user's Local is the Metagraph `local_knowledge:<user_id>`. Therefore `delete` MUST NOT drop the FalkorDB graph or run a blanket `MATCH (n) DETACH DELETE n` — that would destroy the co-resident Global and other users' Locals. Instead it resolves the Local's `metagraph_id` (via `MetagraphLoader.find_by_name`) and runs a scoped multi-statement `DETACH DELETE`: graph elements (`(:Graph)<-[:IN_GRAPH]-`), tombstones (by `graph_id`), source-side XRefs, anchor-attached satellites (metaedges / metahyperedges, `(m)--(sat) WHERE NOT sat:Graph`), the contained `:Graph` nodes, and finally the `:Metagraph` anchor.

Because Falkor delete-then-recreate is non-atomic under the single-process multi-threaded model (ADR-0009 / D32), `save` and `delete` hold the per-user `UserMutexRegistry` mutex (ADR-0006) for the write. The scoped-delete statement set is **gate-verified** against a live FalkorDB (the sandbox has no FalkorDB); metaedge/XRef coverage completeness is a known follow-up surface (design log §6).

### 2. Protocol keeps the `Metagraph` shape

The `LocalPersister` Protocol trafficks in live `Metagraph` (ADR-0011 §amendment-2 clause 1, retained). No `MetagraphDump` enters the Protocol.

### 3. `SQLiteLocalPersister` + `MetagraphDump` + serializer promotion — **deferred**

All three defer to the first phase with a local-first / portable-export consumer. At that phase: promote the `mindsos_cli` state-file serializer (`graph_to_state` / `state_to_graph` / `metagraph_to_state` / `state_to_metagraph`) into `mindsos_core` with dependency-injected graph/schema resolvers, compose a self-contained `MetagraphDump` envelope, and store it as an opaque blob in a dedicated `locals.db` (never `server.db`). ADR-0004 stays unamended until then.

## Rationale

- **Falkor is the consumer-backed path and needs zero new serialization.** Native `persist` / `load` already exist and are core-resident (server-safe).
- **Defer the speculative store.** The SQLite path's only justification was a future local-first deployment; building its serializer now — at real refactor cost and CLI-regression risk — is premature.
- **Mutex on write.** The single-process multi-threaded model still races on a non-atomic delete-then-recreate; the existing per-user mutex closes the window without a new primitive.

## Consequences

- v1 Local persistence is FalkorDB-only; `InMemoryLocalPersister` remains the test/diagnostic impl.
- `MetagraphDump`, `SQLiteLocalPersister`, `locals.db`, and the serializer promotion are tracked as a deferred bundle (see Phase 44 design log §5 + §6).
- The persister is configured once at `MindsOSServer` construction (ADR-0011 §amendment-3) and held for the process lifetime.
- ADR-0004 needs no amendment at v1 (no SQLite-blob Local store ships).

## Alternatives considered

1. **Ship both stores now (CR-2 original).** Rejected on investigation — the SQLite serializer is a disk-coupled refactor with CLI-regression risk for a consumer-less store.
2. **Net-new self-contained serializer for the SQLite path (Opt-3b).** Rejected for v1 — still builds a serializer (and a duplicate format) for a store with no consumer.
3. **Promote + dependency-inject the CLI serializer now (Opt-3a).** Rejected for v1 — correct eventual design, but premature; it lands with the first SQLite consumer.

## §amendment-1 (feat/f9-durable-local — 2026-06-21): FalkorDBLocalPersister promoted to live surface

F9 (ADR-0186) promotes `FalkorDBLocalPersister` from dormant
(module-`__all__` only, no consumer) to live public surface — re-exported
from `mindsos_server.persistence.__all__` and consumed by
`mindsos_server.local_boot.load_or_mint_local` as the durable backing
store for per-device Locals. A role-scoped `reset_run_state` is added
alongside the hard `delete` (ADR-0187).
