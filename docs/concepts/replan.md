# Replan

Replanning lets a task recover from a step that diverges from expectation
without discarding the reasoning it has already done. The model is Chat A D14 +
Chat B D-B36, implemented at Phase 47 in `mindsos_intelligence/replan_check.py`
(ADR-0173).

## Dispatch and verdict

The decision is an L3 capacity: L4 dispatches `decision.should_replan(state,
divergence)` and acts on the returned **ReplanVerdict** — `decision ∈
{continue, replan, abort}` plus `verified` and `divergence` metadata. L4 owns
only the dispatch and the resulting control flow (the strict line: dispatch is
L4, the decision is L3).

## Invalidate-at-and-below

A `replan` verdict carries a `replan_level ∈ {hint, map, plan, plan_subtree,
pipeline}`. The orchestrator invalidates chain artifacts **at and below** that
level and re-enters the lifecycle there; everything upstream (hints, mapping,
the Plan above the replan point) is **reused**. Invalidated artifacts are kept
in the chain marked `aborted_for_replan_at_level_L` for audit — they are not
deleted.

At Phase 47 the v0 replan level is `pipeline`: the TaskRun's PipelineRuns are
the at-and-below set, cleared and re-executed; the upstream Plan/Mapping/HintSet
are reused.

## Budgets and records

Replans are bounded: `per_milestone_replan_budget = 2` and
`per_task_total_replan_budget = 5` (both admin-tunable). On budget exhaustion
the path falls through to the appropriate `DontKnowReason`.

A **ReplanRecord** is emitted into intelligence-MM **only** on `replan` or
`abort` verdicts — `continue` produces no record (sparse provenance). The
record carries the replan level, the verdict, and the invalidated/spawned chain
refs, with bidirectional XRefs to the TaskRun's `replan_history`.

## Phase 47 behaviour

The `decision.should_replan` body is the v0 stub, whose verdict is
test-configurable so the ReplanRecord-emit + invalidate path is exercised. The
concrete replan-decision body ships in WSD installation.
