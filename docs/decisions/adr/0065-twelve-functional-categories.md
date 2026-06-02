---
title: Twelve functional categories as the node-graph partition
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-006]
---

# ADR-0065: Twelve functional categories as the node-graph partition

**Status:** Accepted

**Date:** 2026-04-21

## Context

Every capacity needs a home. Putting them all in one graph makes auto-discovery scan a large index; partitioning by category keeps discovery fast.

## Decision

Twelve `CATEGORY_*` constants (perception, comprehension, derivation, decomposition, combination, path-finding, retrieval, scoring, trace, signalling, interaction, learning-methods). Every `_CapacityBase.category` must be one of these. Each category gets its own role-graph under both Global and Local metagraphs.

## Consequences

**Good:**
- Readable partition; small per-category graphs; cheap auto-discovery.

**Bad:**
- Extension is a single file-edit rather than a config flag.

## Alternatives considered

1. **Free-form category strings** — rejected because typo drift would fragment.
2. **A hierarchy of categories** — rejected as premature; 12 flat buckets are easier to browse.

## §Implementation (Phase 28 — 2026-05-24)

Shipped Phase 28:

* The 12 `CATEGORY_*` constants ship at Phase 27 (`mindsos_capacity/identifiers.py`); `FUNCTIONAL_CATEGORIES` frozenset enumerates them. Phase 28 makes them concrete as 12 `Graph` instances inside the Global L3 Metagraph via `mindsos_capacity.bootstrap.create_global`.
* `mindsos_capacity.bootstrap.ensure_category_graph(metagraph, category)` lazily creates a category role-graph in Local metagraphs (Locals start empty per [[ADR-0061]]).
* Schema for every `capacity:<category>` graph: `mindsos_capacity.schemas.build_category_schema` (3 NodeTypes: `Capacity`/`Monitor`/`Adapter`; 4 EdgeTypes: `TYPE_COMPAT`/`CONSTRAINT`/`PRODUCES`/`CONSUMES` — last two reserved-not-populated per [[ADR-0064]] §Implementation).
* **Phase 15b PB-23 carry-forward RESOLVED at Phase 28:** alignment-lookup is a RETRIEVAL capacity (a capacity that ships in the `retrieval` category and reads alignment edges from KL's `alignments` role-graph), NOT a 13th L3 category. The 12-category contract is unchanged. AlignmentsImporter ship-slot remains "build for first consumer" per PHASE_15b PB-23 lock E4; no schedule change.

Status remains Accepted; no contract change (12 categories remain canonical).
