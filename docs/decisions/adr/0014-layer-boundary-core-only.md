---
title: Layer boundary - Core owns primitives, schema, identity, persistence, reconstruction only
status: Accepted
date: 2026-04-22
layer: L1
aliases: [core-ADR-001]
---

# ADR-0014: Layer boundary - Core owns primitives only

> *See `confirmation_docs/PHASE_MAP.md` §5 for amendments through Phase 05d (Phase 05b first amendment, Phase 05c second amendment, Phase 05d third amendment). Inline transcription deferred to Phase 38 per shipped precedent.*

**Status:** Accepted

**Date:** 2026-04-22

## Context

The 5-layer architecture needs a sharp line between "data" and "reasoning". Mixing them in Core would couple schema evolution to knowledge semantics, and would make every higher-layer test transitively depend on Core's reasoning logic.

## Decision

Core owns only data primitives (`Node`, `Edge`, `HyperEdge`, `Graph`, `MetaEdge`, `MetaHyperEdge`, `Metagraph`), schema, identity, persistence, and reconstruction. It performs **no** reasoning, derivation, reference walking, cross-ref validation, caching, transactions, migrations, or concurrency control. A Core module importing from a higher layer is a bug.

## Consequences

**Good:**
- Core is small (~2.5k LOC), readable end-to-end in a sitting, and can be tested without any domain data.
- Higher layers inherit a minimum-surprise substrate.
- Layer isolation is achievable — no circular dependencies at the primitive level.

**Tradeoff:**
- Every higher layer re-implements some domain glue (ref integrity, migration, dry-run). Several of these have become their own ADRs.

## Alternatives considered

1. **A "thick Core" that bundled reasoning helpers** — rejected because it couples schema/cypher churn to knowledge semantics.
2. **A split into `mindsos_core_data` + `mindsos_core_persistence`** — see ADR-0018 (Single Core package).
