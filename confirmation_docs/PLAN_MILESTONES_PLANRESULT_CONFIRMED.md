# plan_construction.build → PlanResult map/fold milestones CONFIRMED (Option A)

**Status:** SHIPPED + MERGED to `main` — PR #96 (squash `ee453be`), tag **`planwire-confirmed`**.
**Gate:** full containerized run (Linux, live FalkorDB, 2026-07-29) = **4383 passed / 12 skipped / 1 xpassed / 0 failed**, 39m. `main` baseline + 5 new; 0 regressions. The lone `xpassed` is the pre-existing Falkor live-persister sweep probe (`tests/maintenance/test_l0_25_falkor_local_persister_live.py`), unrelated.
**core_version:** stays `phase50` (L4-side wiring; no core-package / role / category change).
**CR / design:** the arc1-brain "thread planner map/fold shape into PlanResult" CR. Relates ADR-0171 (lifecycle); **ADR-0199 PRESERVED** (L4 owns the unpack loop; the shape rides the planner's `DS_PLAN` output, core stays agnostic). No new ADR (additive wiring).

## What this is

The collection-iteration map/fold executor (Slices 1b/2/3b — `COLLECTION_ITERATION_SLICE_1B_CONFIRMED.md` et al.) was shipped but **unreachable through the normal lifecycle**: `plan_construction.build` is the sole `PlanResult` producer (`orchestrator.py`), and it never populated the `milestone_specs` / `leaf_targets` fields `execution.run` reads. Map/fold only ran in tests that called `execution.run` directly. This change wires `build` so a planner's map/fold plan actually reaches the executor — a generic core completeness fix (any brain), not arc-specific.

## What shipped (1 edited, 1 new test)

- **`mindsos_intelligence/plan_construction.py`** — `build` now reads an optional ordered `plan_out["milestones"]` list, each entry `{"spec"?: <map|fold descriptor>, "leaf_target"?: {start_datastate, target_datastate}}`. When present it emits one leaf Milestone per entry (in planner order) under a synthetic **non-leaf root**, builds a Pipeline per leaf, and assembles `milestone_specs` / `leaf_targets` keyed to the milestone refs **core mints** (locked decision 3: the consumer's planner emits the shape; core owns ref identity + emission). The plan-global `solve_target` is still read (`_read_solve_target`) for the per-leaf fallback (`execution.run`: `endpoints = leaf_targets.get(ref) or solve_target`). Helpers `_read_milestones` / `_read_leaf_target` / `_build_from_milestones`. `milestones` absent / `[]` / malformed → `_read_milestones` returns `None` → **byte-identical v0** (`root` + `_decompose_recursive` + `solve_target` only). The v0 path and `_read_solve_target` are untouched.
- **`tests/phase_48/test_plan_milestones_build.py`** (NEW, 5) — (1) milestones populate `PlanResult` in planner order, keyed to emitted refs, no v0 decompose dispatch; (2) per-leaf `leaf_target` + plan-global `solve_target` coexist; (3) no/empty/malformed `milestones` is byte-identical to v0; (4/5) end-to-end: a `build()`-produced plan drives the **real map/fold executor** (map fans over the collection in order, fold reduces the ordered outputs).

## Option A — the pinned planner contract

A planner returns, on the solve path:

```
plan_out = {
  "milestones": [
    {"spec": {"kind": "map", "collection_ds": ..., "member_ds": ..., "sub_target": ..., "out_ds": ...}},
    {"spec": {"kind": "fold", "reducer_iri": ..., "in_ds": ...}},
  ],
  "solve_target": {...}?,
}
```

Key names are now the contract: **`milestones` / `spec` / `leaf_target`**. Consumers pin their `derive_initial_plan` shadow to these.

## Still owed (consumer side, NOT core)

arc's `derive_initial_plan` shadow (`arc1-brain/arc1_brain/arc_plan.py`, main `bbee199`) still emits a **single-target** plan (`SOLVE_TARGET_DS = DS_RAW_PAIRS`, `single_milestone: True`) — no `milestones`. The CR's claim that "arc has a red test staged that asserts a map/fold plan reaches the executor" does **not** hold against arc's repo (its only test is single-target groundwork, already green). arc owes: write the map/fold `derive_initial_plan` + a real test, pinned to the key names above. `arc.raw_pairs` is already a proper collection DataState (`member_ds = arc.raw_pair`).
