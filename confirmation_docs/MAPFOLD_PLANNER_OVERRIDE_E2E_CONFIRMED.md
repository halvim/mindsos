# Map/fold planner-override end-to-end — CONFIRMED (test-only)

**Status:** SHIPPED to `main` (PR #101 squash) — merged-state Linux gate **4422 passed / 12 skipped / 1 xpassed / 0 failed** (containerized full, live FalkorDB, 2026-07-30). Baseline `main` @ `8451997` = 4421 (DREAM_PRE0_SLICE3_CONFIRMED) **+1** = the one new test. 0 regressions.
**core_version:** unchanged (phase50). **Test-only — no production code change.**

## What
New `tests/phase_48/test_planner_override_e2e.py` (1 test) proving the never-before-exercised link on the collection-iteration map/fold seam: a **real registered `derive_initial_plan` override** emits a map/fold `milestones` shape that resolves through a **real `L4Dispatcher`** in `plan_construction.build`, and the built plan drives the executor's fan-out + fold end-to-end.

The test registers the v0 builtin `derive_initial_plan`, then **overrides its implementation in place** (`register_capacity(..., if_exists="upsert")` -> `_declarations` swap; the historically-fragile path, ADR-0156 §amendment-1) with a body returning `{DS_PLAN: {"milestones": [map, fold]}}`. It calls `plan_construction.build` with the real dispatcher, asserts `milestone_specs` populated in planner order, runs `execution.run`, and asserts the members fan out in collection order and the fold receives the ordered member outputs.

## Why
The map/fold executor shipped in Slices 1b/2/3b, and #96 wired `plan_construction.build` to thread a planner's `milestones` into `PlanResult`. But the only end-to-end coverage (`test_plan_milestones_build.py`) fed `milestones` via a **fake planner-dispatcher** — so no test proved that a **brain-registered** planner override (the exact mechanism a consumer brain uses, locked decision 3) is what a real dispatch resolves. Two-tier Local-over-Global resolution is not on `main`, and no brain had ever overridden `derive_initial_plan`, so this path was plumbed-but-unproven. This test closes that gap and makes "a brain can emit map/fold plans today" a gate-covered guarantee.

## Consumer impact
Unblocks the nilm recognition migration (and arc's) with a proven path: register a `derive_initial_plan` (via `if_exists="upsert"`) that emits `plan_out["milestones"]`, and the shipped executor fans out + folds through `run_lifecycle`. Consumers also need the map's `out_ds = reduction.scored_collection` and each member `sub_plan` ending in `{score,label}` (see `COLLECTION_MAP_FANOUT_COORDINATION`).

## Scope / non-goals
Proves `override -> build -> executor`. Does NOT route through full `run_lifecycle` (Phase-1 interpretation + episode open/close are covered elsewhere and are not where the risk was). No production code touched; `reduction_v0` and the executor unchanged.
