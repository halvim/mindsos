---
title: Batched writes via UNWIND, one batch per relationship type
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-009]
---

# ADR-0022: Batched writes via UNWIND, one batch per relationship type

**Status:** Accepted

**Date:** 2026-04-22

## Context

Persisting a 10k-node graph as 10k `MERGE (n:Node {...})` statements is N+1 round-trips to the driver. At realistic graph sizes this dominates persist latency.

## Decision

Repositories batch writes per-type using `UNWIND $rows AS row MERGE (n:Node {id: row.id}) SET n += row.props`. Each relationship type gets its own batch, because rel-type names can't be parameterised (see ADR-0021).

## Consequences

**Good:**
- Linear scaling in graph size.
- Latency bounded by round-trip count (≈ number-of-distinct-rel-types).

**Bad:**
- One failing row aborts the whole batch.

## Alternatives considered

1. **Single statement per row** — rejected because it's N+1.
2. **Single global UNWIND across all rel types** — rejected because Cypher can't templatise rel-type per-row.
