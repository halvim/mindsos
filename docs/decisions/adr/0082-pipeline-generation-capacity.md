---
title: Pipeline generation is itself a category of capacity in L3
status: Deferred
date: 2026-04-22
layer: L3
aliases: [capacity-ADR-023]
---

# ADR-0082: Pipeline generation is itself a category of capacity in L3

**Status:** Deferred — acknowledged with a known path forward but not implemented in v1; revisit post-v1. Reconciled in the 2026-07 doc-vs-code audit.

**Date:** 2026-04-22

## Context

The latest design pass clarified a division of labour: the Intelligence Layer (L4) is responsible for *running* pipelines and re-evaluating them mid-flight, but the *procedures* that actually assemble a pipeline — map a task to a pipeline, order steps, pick among alternates, produce a fallback plan — are themselves stable functions. They fit L3's "fixed, not learned" definition (ADR-0060) and should live where every other stable function lives.

## Decision

Introduce pipeline-generation procedures as first-class capacities in L3. They fit under one of the existing categories (likely `CATEGORY_COMBINATION` or a new `CATEGORY_PLANNING`; decision deferred to the implementation PR). Examples: `capacity:combination:bfs_pipeline_finder` (the current `find_pipeline` reframed), `capacity:combination:map_task_to_pipeline`, `capacity:combination:reorder_for_constraints`. L4's orchestrator invokes them via the usual `cl.invoke(...)` path, feeding them the current task, the current metagraph view, and the set of constraints to respect.

## Consequences

**Good:**
- Pipeline generation is inspectable, swappable, and auditable like any other capacity.
- Different strategies (BFS, Dijkstra-with-constraint-weights, user-authored heuristic) can coexist as alternates behind `CONSTRAINT_MUTUALLY_EXCLUSIVE`.
- L4's orchestrator shrinks: it becomes a dispatcher plus a mid-flight re-planner, not a planner-of-first-resort.

**Cost:**
- The current `mindsos_capacity.builtins.find_pipeline` needs to be reframed as a `Capacity` declaration rather than a bare function.

## Alternatives considered

1. **Keep pipeline generation inside L4** — rejected (forces every alternative strategy to be an L4 code branch rather than a data/declaration change).
2. **Put it in L5** — rejected (L5 is a mental-model consumer, not an algorithm store).

## Open items before flipping to Accepted

(a) Which category to use. (b) Whether the `context` schema needs a formal "planning context" field. (c) How mid-flight re-planning passes partial-execution state back into a generation capacity.
