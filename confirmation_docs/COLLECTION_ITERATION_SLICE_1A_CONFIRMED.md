# Collection-iteration Slice 1a CONFIRMED — cross-milestone value bus

**Status:** BUILT + GATE-GREEN on `feat/collection-iteration-slice-1a` (commit `9bdd026`) — NOT merged (PR / rebase onto main pending).
**Gate:** full containerized run (Linux, live FalkorDB, 2026-07-25) = **4311 passed / 12 skipped / 1 xpassed / 0 failed**, 32m17s. Baseline + 2 new (the Slice-1a value-bus tests); 0 regressions.
**Targeted pre-gate:** `pytest tests/phase_48/test_slice1a_value_bus.py tests/phase_48/test_step5_solve_execution.py` = 10 passed (2 new + 8 Step-5 regression).
**core_version:** stays `phase50` (L4/L5-side; no core-package / role / category change).
**CR / design:** `confirmation_docs/CORE_CR_COLLECTION_ITERATION.md`. Relates ADR-0171 (lifecycle); ADR-0199 PRESERVED.

## What this slice is

The first slice of the collection-iteration CR (arc's reason-half blocker). Before it, `execution.run` ran each leaf's pipeline in its own blackboard seeded identically from `solve_seed` and discarded the outputs — no value could flow between milestones, so every real solve was single-leaf. This slice adds the **cross-milestone value bus**: a run-scoped, attempt-scoped blackboard threaded across leaves, so a downstream stage consumes what an upstream stage produced. No map/fold fan-out yet (Slice 1b).

## What shipped (2 edited, 1 new test)

- **`mindsos_intelligence/execution.py`** — `run()` holds one `blackboard = dict(solve_seed or {})` created per call (attempt-scoped: discarded on return, so a replan re-enters clean). Each leaf seeds `execute_pipeline` from the blackboard **filtered to the pipeline's `start_datastates`** (so `execute_pipeline` does not mint unrelated blackboard values as grounding roots — `pipeline_execution.py:135-141`), then `blackboard.update(result.outputs)` threads its produced values downstream. `_run_leaf_pipeline` now takes `endpoints` + `blackboard` and returns `result.outputs`. The `real_mode` gate generalized to `mm and solve_seed and (solve_target or leaf_targets)`.
- **`mindsos_intelligence/plan_construction.py`** — additive `PlanResult.leaf_targets: Optional[Dict[str, Dict[str, str]]] = None` — per-leaf `{start_datastate, target_datastate}` for a multi-stage plan whose leaves form a value chain. A leaf with no entry falls back to the plan-global `solve_target`. The v0 builder never sets it.
- **`tests/phase_48/test_slice1a_value_bus.py`** (NEW, 2) — a 2-stage synthetic plan (`raw_task → raw_grids`, `raw_grids → answer`) proving stage B receives exactly stage A's output (`raw_grids` is never in the seed), plus attempt-scoped freshness across two `run()` calls.

## Inertness (no regression to shipped paths)

With a single-leaf plan and no `leaf_targets` — today's v0 + Step-5 path — the sole leaf seeds from the blackboard initialised to `solve_seed` (== `dict(solve_seed)` before) and merges outputs no one reads: **byte-identical**. The change only activates for a plan with >1 stage or a `leaf_targets` entry. Same additive-inertness basis as L5 Step 5; the 8 Step-5 regression tests pass unchanged.

## Verified substrate facts (why 1a needed a value bus at all)

- No cross-milestone value threading existed: `execution.run` discarded `result.outputs`; `execute_pipeline` is one pipeline / one pass / one value per DS (`pipeline_execution.py:116,155-206`).
- `mm_handle` / `MMResolver` reads long-term L2 knowledge (pinned), not the run's working values — so the bus is in-memory, not a capacity_mm read surface.
- Replan stays clean: `replan_check.check` / `sufficient_predicate.evaluate` dispatch empty state; `invalidate_at_and_below` only clears `task_run.pipeline_runs` (`replan_check.py:32-43`). Attempt-scoped blackboard → no stale reads.

## Open sub-item (deferred within the CR)

Cross-stage **grounding** continuity: value threading is in-memory, so a downstream leaf's seeded start grounds as a fresh root in its own per-run graph rather than linking to the upstream leaf's output instance. Accepted for 1a; revisit under Slice 2 (run-ref path).

## Next

Slice 1b — map/fold milestone kinds + executor fan-out + ∀-abort barrier + bounded retry (cap 2, `MEMBER_RETRY_CAP`) + per-member grounding + fold dispatching an L3 reducer over ordered member outputs (sequential members). Then Slice 2 (nesting), Slice 3 (per-member replan via the reserved `"map"` / `"plan_subtree"` levels, `replan_check.py:19`).
