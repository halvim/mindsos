---
title: Replan-check dispatch + invalidate-at-and-below + ReplanRecord sparsity
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L4
related: [0171, 0172]
---

# ADR-0173: Replan-check dispatch + chain invalidation

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0171 (six-phase lifecycle), ADR-0172 (Phase-1 + v0 catalog).

## Context

Chat A D14 + Chat B D-B36 settled the replan model: the orchestrator periodically checks whether to replan, and a replan **invalidates chain artifacts at and below the replan level**, reusing upstream artifacts. The decision is an L3 capacity (`decision.should_replan`); the dispatch + record-keeping is L4 control flow (the strict line — dispatch L4, decision L3).

## Decision

### 1. Dispatch (L4) + decision (L3)

L4 calls `decision.should_replan(state, divergence) -> ReplanVerdict` at the between-step check points. `ReplanVerdict(decision, verified, divergence)` — `decision ∈ {continue, replan, abort}` + 2 metadata fields (Chat A R2). The capacity is an L3 decision; the orchestrator only dispatches it and acts on the verdict.

### 2. Invalidate-at-and-below (D-B36)

A `replan` verdict carries a `replan_level ∈ {hint, map, plan, plan_subtree, pipeline}` (+ optional `replan_milestone_ref`). The orchestrator invalidates chain artifacts **at and below** that level and re-enters the lifecycle there; upstream artifacts are reused. Invalidated artifacts are marked `aborted_for_replan_at_level_L` (retained in the chain for audit, not deleted).

Budgets: `per_milestone_replan_budget = 2`, `per_task_total_replan_budget = 5` (both admin-tunable). On budget exhaustion the path falls through to the appropriate `DontKnowReason` (e.g. `PIPELINE_UNAVAILABLE`).

### 3. ReplanRecord sparsity (D14)

A **ReplanRecord** is emitted to intelligence-MM **only on `replan` or `abort` verdicts** — `continue` verdicts generate no record. The record extends the Chat A D14 schema with `replan_level` + `replan_milestone_ref` and bidirectional XRefs to TaskRun (`replan_history`) and the invalidated/spawned chain artifacts.

## Rationale

- **Dispatch/decision split** keeps the replan policy learnable in L3 while L4 owns the mutation (invalidation) and record-keeping.
- **Invalidate-at-and-below** reuses expensive upstream work (hints, mapping) when the failure is local.
- **Sparse records** avoid a per-step firehose; only genuine replan/abort events are provenance-worthy.

## Consequences

- At Phase 47 the `decision.should_replan` body is a test-configurable v0 stub (ADR-0172) so the invalidation + ReplanRecord-emit path is exercised by forcing a `replan`/`abort` verdict; the production body ships in WSD installation.
- Replan re-entry runs on the same worker thread as the lifecycle (ADR-0171) — no cross-thread coordination.

## Alternatives considered

1. **Record every check (including `continue`).** Rejected — per-step firehose; D14 chose sparsity.
2. **Invalidate the whole chain on any replan.** Rejected — discards reusable upstream work; D-B36 chose at-and-below.

## §v2-reservations

- Per-Milestone declared `on_child_failure` policy (currently fail-fast v1).

## §Implementation (Phase 47; pending ship)

`replan_check.py` (dispatch + ReplanRecord emit + invalidate-at-and-below) + `tests/phase_47/test_replan_check_dispatch.py` (forces `replan`/`abort` via the v0 stub).
