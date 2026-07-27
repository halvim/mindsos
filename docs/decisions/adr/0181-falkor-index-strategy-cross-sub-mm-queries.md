---
title: Falkor index strategy for cross-sub-MM hyperedge queries
status: Accepted
date: 2026-06-09
accepted_date: 2026-06-09
layer: L0
related: [0160, 0176, 0121]
---

# ADR-0181: Falkor index strategy for cross-sub-MM hyperedge queries

**Status:** Accepted

**Date:** 2026-06-09

**Related:** ADR-0160 (FalkorDBLocalPersister — native round-trip), ADR-0176 (consolidation → Episode/Memory/`MEMORY_CONTAINS_EPISODE`), ADR-0121 (FalkorDB as the graph store).

## Context

Chat B routed **PB-HHH** ("Falkor query indexes for cross-sub-MM hyperedge queries"; `_workbench/L5_FUTURE_WORK.md` L5-NEW-13; PHASE_MAP §7 q2) to **Phase 49 R0** for decision. The question: which cross-sub-MM queries — Pipeline → member CapacityInstances/DataStateInstances via `IntergraphHyperEdge`, the `MEMORY_CONTAINS_EPISODE` Memory→Episode association, and Episode lookup by request-pattern — need FalkorDB indexes to stay performant at scale?

Phase-49 grounding (probe-first, `PHASE_49_DESIGN_LOG.md` §2 finding 4): **there is no indexed-query consumer in v1.** The shipped persistence path is whole-metagraph save/load — `FalkorDBLocalPersister.save`/`load` round-trip the entire Local Metagraph natively (ADR-0160); reads walk an in-memory `MetagraphView` (`get_node`/`get_edges`), not a Cypher query against Falkor. The future consumers of an *indexed* query are all deferred:

- WSD retrieval (episode lookup by request-pattern / Memory cluster walk) — WSD installation chat.
- Memory-cluster secondary index (L5-NEW-11) — v2 if query volume.
- Dream candidate scans over the episode corpus — currently pulled in-process from a descriptor list (ADR-0178), not queried.

Shipping index DDL now would be **speculative**: the index set is best chosen *with* the retrieval query shapes, which do not exist until WSD lands.

## Decision

**Decide-and-document; ship zero index code (PB-HHH-A).** Ratify the index *strategy* here and in the `usage/cookbook/end-to-end.md` "Scaling" section; defer physical index creation to the first real query consumer.

The strategy — the indexes the future query consumer SHOULD create, recorded so that chat applies them verbatim rather than re-deriving them:

1. **`Episode.request_pattern_iri`** — a node label+property index `CREATE INDEX FOR (e:Episode) ON (e.request_pattern_iri)`. Consumer: "episodes for request-pattern X" retrieval (the primary-cluster lookup, Chat B D-B54).
2. **`Memory.memory_id`** — `CREATE INDEX FOR (m:Memory) ON (m.memory_id)`. Consumer: Memory-composite lookup during consolidation's materialise-once-per-pattern check at scale (today an in-memory walk).
3. **`IntergraphHyperEdge` membership** — index the membership relation's property used by Pipeline→member walks once cross-sub-MM queries run as Cypher (today the walk is in-memory `MetagraphView`).

**No `mindsos_server/persistence/indexes.py`, no migration scripts ship at Phase 49.** This is the explicit content of the decision, not an omission. The `test_falkor_index_present.py` test named in the PHASE_MAP Phase 49 row is therefore **not authored** (nothing to assert); the decision is anchored by `tests/phase_49/test_adr_amendment_sentinels.py` against this ADR.

## Rationale

- **Consumer discipline.** Every Phase 39–48 chat deferred absent-consumer surfaces; an index with no query path is exactly such a surface. Shipping it would add maintenance + a speculative commitment to the wrong properties.
- **The decision still closes q2.** PB-HHH demanded a *decision*, not necessarily code; the strategy + the ADR satisfy "index definitions land in the cookbook page + an ADR if substantial."
- **FalkorDB semantics are recorded.** FalkorDB supports `CREATE INDEX ON :Label(prop)` (and full-text indexes); the consumer chat applies the three indexes above against its real query shapes.

## Consequences

- **Routing.** `_workbench/L5_FUTURE_WORK.md` L5-NEW-13 owner updated: *strategy ratified (ADR-0181 @ Phase 49); physical creation → WSD retrieval (first query consumer).*
- **No performance change at v1** — whole-graph save/load is unaffected; trivial-task scope has no query volume.
- **Reversal trigger.** If a pre-WSD consumer materialises an indexed Cypher query against the cross-sub-MM topology, re-open here and ship `indexes.py` with that query's shape.
