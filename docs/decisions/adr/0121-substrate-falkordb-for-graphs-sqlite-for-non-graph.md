---
title: Substrate — FalkorDB for graphs, SQLite for non-graph state
status: Proposed
date: 2026-04-27
layer: L1
---

# ADR-0121: Substrate — FalkorDB for graphs, SQLite for non-graph state

**Status:** Proposed

**Date:** 2026-04-27

**Related:** ADR-0004 (split persistence — extended), ADR-0030 (Client protocol). This ADR is the umbrella commitment under which ADR-0122 through ADR-0127 land specific FalkorDB-weakness mitigations.

## Context

The 2026-04-27 L1 redesign critique surfaced ADR-025 in the design-critique handoff: "re-evaluate FalkorDB as the persistence substrate." The substrate question hadn't been re-litigated since FalkorDB was chosen for v1, and several Core-layer pain points (no transactions, no async, no procedures, no row-level locking, no streaming reads, no native vector search) were treated as "FalkorDB facts of life" rather than evaluated against alternatives (Memgraph, Neo4j, KuzuDB, Postgres+AGE).

The pivot's release model adds a SQLite version DB alongside SQLite `server.db` (auth/sessions/audit), making the substrate landscape concretely heterogeneous: graphs in FalkorDB, non-graph state in SQLite.

The L1 redesign session evaluated alternatives and decided.

## Decision

**FalkorDB stays as the graph substrate.**

The decision was made on grounds of speed (FalkorDB's GraphBLAS sparse-matrix traversal is fast on the workloads MindsOS exercises). A formal benchmark against Memgraph / Neo4j / KuzuDB on actual MindsOS workloads (KL OEWN import, KL promote round-trip, capacity discovery, MetagraphLoader full reload) is **open but not blocking**; document the numbers when collected.

**Constraint that follows:**

> Any layer working with graph data uses FalkorDB. SQLite is reserved for non-graph data: `server.db` (auth/sessions/audit), `version_db` (pivot release manifest, node versions, peer deps, rewrite maps), and any future non-graph need.

This commits the project to a heterogeneous-substrate architecture where FalkorDB + SQLite + (in v2) external ANN index for vectors form the storage layer.

**Six paired weakness mitigations (each its own ADR):**

| Weakness | Mitigation | ADR |
|----------|-----------|-----|
| W1 — No multi-statement transactions | Hybrid: idempotent writes + WAL graph for promote/release-ship | 0122 |
| W2 — No DB-level constraints (no UNIQUE, no FK) | Indexes + persist-time check + per-layer `verify_integrity` | 0123 |
| W3 — No streaming reads / no pagination | `iter_load(batch_size)` + `MetagraphLoader.refresh(role)` | 0124 |
| W4 — Memory-only operation | Lazy Local hydration + LRU eviction (server-side) | 0125 |
| W5 — No async client | `AsyncClient` Protocol via `asyncio.to_thread` | 0126 |
| W6 — No row-level locking | Optimistic concurrency on Global writes (`_version` property) | 0127 |

**Deferred weaknesses** (not v1 blockers; tracked in `docs/decisions/proposed.md`):

- W7 vector indexing (verify FalkorDB version when L4 retrieval starts)
- W9 observability hooks (defer until first slow-persist debugging)
- W10 InMemoryClient fidelity (Docker fixture pattern documented)
- W11 tri-store consistency matrix (failure-mode enumeration deferred to ADR-0114)
- W12 horizontal scale / clustering (per-user-shard pattern documented; defer code)

## Rationale

FalkorDB is fast enough that switching substrate would force the project to re-prove every existing test. The substrate-level weaknesses are real but each has a bounded mitigation that can ship without changing the substrate. The cumulative cost of mitigations (~1300–1500 LOC across L1) is smaller than the cost of swap (re-prove 360+ tests, re-port Cypher patterns, retrain mental model).

The "speed" justification is informal until benchmarked. ADR records the decision to commit; benchmarking is owed work that can land independently. If benchmarks reveal Memgraph is meaningfully faster on actual workloads, the substrate question reopens; the L1 redesign work documented here is reversible at the cost of one substrate-port PR.

## Consequences

**Good:**

- Substrate decision is locked; no further re-litigation in L1 redesign.
- The mitigations (0122–0127) are bounded and independently shippable.
- KL/L3/L4 design can assume the FalkorDB + SQLite combination as a stable platform.

**Tradeoffs:**

- Six mitigation ADRs is non-trivial implementation surface (~1300–1500 LOC total).
- Each mitigation is technically a workaround; the cumulative complexity is real.
- Benchmark data is owed; until it lands, "FalkorDB is faster" is a claim, not a proof.
- Tri-store consistency (FalkorDB + server.db + version_db) is enumerated only as a failure-mode matrix in v1; outbox/saga patterns deferred (W11).

## Alternatives considered

1. **Switch to Memgraph.** Cypher-compatible, has multi-statement transactions, supports procedures. Rejected — would force re-port of existing FalkorDB-specific Cypher patterns and re-prove of 360+ tests. The transaction win simplifies W1's WAL graph, but the migration cost outweighs.
2. **Switch to Neo4j.** Mature ACID transactions, native graph algorithms. Rejected — heavyweight (Java VM); community-edition clustering limited; biggest mental-model shift.
3. **Switch to KuzuDB.** Embedded, Cypher, ACID. Rejected — younger ecosystem; behaviour on edge cases less documented.
4. **Switch to Postgres + Apache AGE.** Best-in-class ACID; pgvector available. Rejected — different paradigm (relational + graph extension); existing Cypher patterns don't port; team-familiarity advantage of MindsOS-on-graph-DB lost.
5. **Defer the question; ship pivot v1 on FalkorDB; revisit at first scale wall.** Rejected as a pure framing — the L1 redesign work is *exactly* the deferred-no-due-date pattern the design-critique handoff complained about. Either commit to FalkorDB and ship mitigations, or commit to swap. We picked commit.
6. **Multi-substrate adapter** (run on FalkorDB or Memgraph based on config). Rejected — doubles persistence-test surface; substrate-specific quirks leak through any adapter; pays for flexibility no current consumer needs.

## Implementation references

- Six mitigation ADRs (0122–0127) cover the load-bearing implementation surface.
- `docs/dev/internals/core.md` updates with the substrate-commitment rationale and mitigation cross-references.
- Benchmark suite TBD; track in `docs/changelog/roadmap.md` under "L1 redesign open items."

ADR moves from Proposed to Accepted when the six mitigation ADRs (0122–0127) reach Accepted state and a user-facing summary of the substrate commitment lands in `docs/dev/internals/core.md`.
