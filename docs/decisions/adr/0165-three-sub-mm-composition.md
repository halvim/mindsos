---
title: Three-sub-MM composition + thin root + no-shadow-state invariant
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L4
related: [0166, 0164, 0162, 0044]
---

# ADR-0165: Three-sub-MM composition + thin root + no-shadow-state invariant

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0166 (MM resolution+instantiation — populates the sub-MMs lazily), ADR-0164 (MM RWLock — guards this structure), ADR-0162 (dream — deep-copies this container), ADR-0044 (episodic_memories — Episodes consolidate from a completed MM).

## Context

Chat B D-B10/D-B11 settled the Mental Model as a **metagraph of three sub-metagraphs**, not a flat graph. L4 substrate (Phase 46) must instantiate the container that Phase 47 (orchestrator) writes chain artifacts into and Phase 48 (L5 v1) consolidates from. The R0 grounding probe confirmed the MM root is brand-new — there is no existing `Schema`/`L2Schema` subclass to reuse — so PB-AAA defaults to building Chat B's schemas as written, with composite-collapse reserved as a post-Phase-49 benchmark-gated optimization.

## Decision

### 1. Three sub-MMs (D-B10)

An MM is a metagraph (graph of graphs) containing three sub-metagraphs:

- **knowledge-MM** — L2 instances pinned for this task (ElementInstance / CompositeInstance of ontology / lexicon / concepts / alignment / episodic_memories nodes).
- **capacity-MM** — L3 `CapacityInstance` + `DataStateInstance` with `produces`/`consumes` intergraph edges (the bipartite topology of ADR-0156, instantiated).
- **intelligence-MM** — L4-authored chain artifacts (HintSet → MappingResult → Plan → Pipeline → PipelineRun → TaskRun, per Chat B), provenance, orchestration state, hint values.

### 2. Thin MM root (D-B10/D-B11)

The MM root is a thin metagraph node holding pointers, not data:

- three sub-MM references (`knowledge_mm_ref`, `capacity_mm_ref`, `intelligence_mm_ref`);
- `task_run_ref` (the TaskRun composite, in intelligence-MM — created Phase 48);
- `ref:problem_trace` (failure detail, per ADR-0096 / unchanged);
- `outcome_ref`.

Chat B schemas are instantiated **as written** (PB-9 / PB-AAA): logical composites, no physical collapse.

### 3. No-shadow-state invariant (D-B11)

**L4 holds no task state outside the MM.** L4 reads only from the MM; on cache-miss it searches L2/L3, instantiates into the appropriate sub-MM (ADR-0166), then reads. Worker-pool threads are L4 substrate (the "L3 worker pool" naming is retired — L3 owns capacities only; threads are L4). This invariant is the substrate's central contract and is asserted by a dedicated Phase 46 test.

### 4. Scope at Phase 46

Phase 46 ships the **container + thin root + the three (initially empty) sub-MM shells + the no-shadow-state invariant**. The 6-level chain artifacts (HintSet…TaskRun) are authored by the Phase 47 orchestrator; `task_run_ref` resolves to nothing until Phase 48. The container is testable now (construct root, attach three sub-MMs, assert cross-MM reference integrity).

## Rationale

- **Three sub-MMs mirror the three layers they snapshot** (L2 / L3 / L4-authored), keeping instantiation dispatch (ADR-0166) a clean IRI-namespace switch.
- **Thin root** keeps the single source of truth in the sub-graphs; the root is navigation only.
- **No-shadow-state** is what makes dream-as-live (ADR-0162) and replan correct — a deep-copy of the MM is a complete, self-contained task state.

## Consequences

- New L4 container type in `mindsos_intelligence/`; uses `mindsos_core` metagraph primitives + `mindsos_instances` instance types.
- The deep-copy primitive (ADR-0162 dream consumer, this phase per PB-6) operates on this container.
- Phase 47 writes chain artifacts into intelligence-MM; Phase 48 consolidates Episodes from a completed MM.

## Alternatives considered

1. **Flat single-graph MM.** Rejected — loses the layer-aligned instantiation dispatch; conflates L2/L3/L4 provenance.
2. **Physical composite-collapse now (PB-AAA).** Rejected — premature; logical schema is the contract; collapse is a measured post-Phase-49 optimization.
3. **Fat root holding inline state.** Rejected — duplicates sub-graph data; breaks the single-source-of-truth.

## §v2-reservations

- Composite-collapse physical layout (post-Phase-49, benchmark-gated).

## §Implementation (Phase 46 — convergence; pending ship)

PR-A: MM container + thin root + three sub-MM shells in `mindsos_intelligence/` (with ADR-0164 lock). Tests `tests/phase_46/test_three_sub_mm.py` (root + three sub-MM refs + cross-MM XRefs) and the no-shadow-state invariant test. Chain-artifact authoring (Phase 47) and consolidation (Phase 48) out of scope.
