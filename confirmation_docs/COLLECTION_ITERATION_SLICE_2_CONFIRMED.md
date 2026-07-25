# Collection-iteration Slice 2 CONFIRMED — map/fold nesting + run-ref path

**Status:** BUILT + GATE-GREEN on `feat/collection-iteration-slice-2` (commit `23da011`) — NOT merged (PR pending).
**Gate:** full containerized run (Linux, live FalkorDB, 2026-07-25) = **4331 passed / 12 skipped / 1 xpassed / 0 failed**, 33m08s (fresh clone `23da011`, `--build`, slice2 collection = 3). `main` baseline (`91269ac`, 4328/0) + 3 new (the Slice-2 nesting tests); 0 regressions.
**Targeted pre-gate:** `pytest tests/phase_48/test_slice2_nesting.py test_slice1b_map_fold.py test_slice1a_value_bus.py test_step5_solve_execution.py` = 17 passed (3 new + 4 Slice-1b + 2 Slice-1a + 8 Step-5 regression).
**core_version:** stays `phase50` (L4/L5-side; no core-package / role / category change).
**CR / design:** `confirmation_docs/CORE_CR_COLLECTION_ITERATION.md`. Relates ADR-0171 (lifecycle); ADR-0199 PRESERVED (collection/member typing consumed, finder never bridges). Builds on Slice 1a (`e9ed6f4`) + 1b (`e24b5c3`).

## What this slice is

Nesting for the map/fold primitive. A map member's per-member work, which in Slice 1b was a single flat `find_pipeline(member_ds -> sub_target)` leaf, may now be a whole **sub-plan** — and that sub-plan may itself contain a map/fold (objects within grids within a task). The core enabling change is that a per-run ref becomes a **path** (`pipelinerun:{scope}:{ref_path}[…]`, a `{milestone_idx}` segment per level and an `m{member_idx}` segment per fan-out), so a nested run's `capacity_mm` grounding graph stays isolated from its siblings and the set of per-run graphs is a tree walkable by path. Members stay sequential (v1); the ∀-abort barrier and bounded retry apply at map-member granularity at **every** level.

## What shipped (2 edited, 1 new test)

- **`mindsos_intelligence/execution.py`** — the Slice-1b run loop is factored so nesting is a recursion:
  - `_run_milestone_sequence` (NEW) — the milestone loop, extracted from `run` and shared by the top level (`ref_path=""`) and each map member's sub-plan (`ref_path` = the member's path). Reads `leaf_targets`/`solve_target`/`milestone_specs` exactly as the old inline loop did; appends every emitted PipelineRun to the flat `task_run.pipeline_runs` (the tree lives in the ref-path — Slice-2 decision). `run` is now a thin wrapper that computes `real_mode` + the attempt-scoped blackboard and delegates.
  - `_run_leaf_pipeline` / `_run_map_milestone` — take a `leaf_path: str` (was `leaf_idx: int`); the per-run ref uses it. At depth 0 the path is `str(leaf_idx)` so the ref is **byte-identical** to Slice 1a/1b.
  - `_run_map_milestone` gains the **`sub_plan` branch (Slice 2)**: when `spec["sub_plan"]` is present, each member runs that nested milestone sequence in its own isolated sub-blackboard (seeded with the member value) under `member_path = f"{leaf_path}:m{member_idx}"`, and the map collects `sub_target` from that sub-blackboard. A nested `MemberAbortError` propagates unretried (all-or-nothing at every level). When `sub_plan` is absent, the member runs the flat 1b path — unchanged. `_run_member_pipeline` / `_run_fold_milestone` are untouched.
- **`mindsos_intelligence/plan_construction.py`** — docstring-only: `PlanResult.milestone_specs` now documents the optional `sub_plan` key on a `map` node (a nested plan `{leaf_milestone_refs, pipeline_refs, milestone_specs, leaf_targets?, solve_target?}` as a plain dict). No logic change — the consumer's planner emits the shape; core stays shape-agnostic (locked decision 3).
- **`tests/phase_48/test_slice2_nesting.py`** (NEW, 3) — over real capacities, no Falkor: (1) an outer map(grids) whose per-grid sub-plan is an inner map(objects) + inner fold, all folded once more at the top — every object runs in order, both fold levels reduce in order, and the four nested per-object grounding graphs carry **distinct role tokens that encode the nesting path** (`run_graph_role` over `pipelinerun:t:0:m{g}:0:m{o}:0:r0`), proving isolation; (2) an inner-member load failure raises `MemberAbortError` that propagates unretried through the outer member, skips the rest, and runs neither fold; (3) retry-then-succeed inside the nested map.

## Inertness (no regression to shipped paths)

`sub_plan` is absent on every v0 / 1a / 1b / Step-5 spec, so every map member takes the flat 1b branch and every non-map milestone takes the existing leaf/fold/notional branch. The ref-path at depth 0 is `str(leaf_idx)`, so per-run refs are **byte-identical** to Slice 1a/1b (verified: `pipelinerun:t:0:m0:0:r0` for a top-level map member; `pipelinerun:t:0:0` for a top-level leaf). The 14 Slice-1a/1b/Step-5 regression tests pass unchanged.

## Design decisions honored (CR §Locked decisions, owner 2026-07-25)

- **Members sequential (v1)** — deterministic grounding order at every nesting level; both fold levels receive outputs in collection order (asserted).
- **Retry cap = 2, ∀-abort at every level** — a nested map enforces its own `MEMBER_RETRY_CAP` + barrier over its members; a nested abort propagates unretried (a deterministic load failure that exhausted its own budget aborts the whole task). A sub-plan member itself is not retried — retry lives at the flat find+execute leaf where transient load failure actually occurs.
- **Consumer emits the shape** — core added only the recursion + the ref-path + the `sub_plan` interpretation; no core planner logic learns arc's structure. The v0 builder never sets `milestone_specs`/`sub_plan`.
- **Provenance = flat run list + path** (Slice-2 decision) — nested milestones emit their own PipelineRuns appended to the same `task_run.pipeline_runs`; the hierarchy is the ref-path (single source of truth), not a parallel nested artifact.

## Deferred: cross-stage grounding continuity (finding)

The CR (`CORE_CR_COLLECTION_ITERATION.md` §Slices) lists Slice 2 as also resolving Slice 1a's deferred **cross-stage grounding continuity**. Verified against the code, that is **not achievable within an additive slice** and is deferred to its own slice:

- Each `execute_pipeline` builds a fresh `CapacityMMWriter` keyed on `(task_id, pipeline_run_ref)` → **one isolated graph per run**, empty index; `PRODUCES`/`CONSUMES` are **intra-graph** edges (`capacity_mm_writer.py`). Slice A chose this deliberately ("sidestep intergraph-edge persistence"; the Slice-B persister takes one per-run graph whole).
- So a consumer stage seeds a value an upstream stage produced as a **fresh root** in its own graph. Linking it to the producer's instance needs an edge spanning two run-graphs — either (a) an intergraph edge (reintroduces the machinery Slice A removed; lives in neither graph, so the persister can't capture it — persistence unbuilt), or (b) sharing one graph across sequential stages (rekey graph on task+attempt; collides head-on with the map's per-member isolation requirement). Both reverse a shipped Slice-A decision and are not byte-identical.
- **What Slice 2 does deliver:** the ref-path makes the set of per-run graphs a **locatable, isolated tree** (naming + isolation) — the weak readability. The **connected cross-stage DAG** (causal edges across stage boundaries) is the strong readability and is deferred. *The CR's Slice-2 continuity bullet should be amended to reflect this split.*

## Abort semantics (recorded)

`MemberAbortError` is unchanged as the ∀-abort signal, caught once in `orchestrator.py` → aborted task (no orchestrator change needed for nesting — a nested abort propagates to the existing catch). With nesting, the exception that escapes `run` names the **innermost** failing member (the deterministic load failure that started the abort); intermediate parent members are not retried. Distinct from a reducer `dont_know` and from a replan, as in 1b.

## Verified substrate facts

- Control-flow validated by dry-running the actual `execution.py` against fakes for the external deps (cloud sandbox) before the gate: double-nested ordering, both fold levels in order, 6 PipelineRuns for a 2×2 nest, inner-abort propagation with `member_index` = innermost, retry-then-succeed, and depth-0 refs byte-identical to 1b. Then confirmed end-to-end over real capacities in `test_slice2_nesting.py`.
- Nested run-graph isolation reuses the Slice-A fresh-ref mechanism: each nested member attempt gets a distinct `pipelinerun:` path ref, so `CapacityMMWriter` mints an isolated graph per nested member (its role token encodes the full path).

## Open items (deferred within the CR)

- **Cross-stage grounding continuity** — its own slice (see finding above); would reverse the Slice-A per-run-graph / intra-graph-edge model.
- **Per-member replan/diagnosis (Slice 3)** — point replan at a specific member via the reserved `"map"` / `"plan_subtree"` REPLAN_LEVELS (`replan_check.py:19`); the ref-path now gives it a precise address.
- **Parallel members** — sequential in v1 by decision; parallel fan-out is a later option.

## Next

Slice 3 (per-member replan), or the continuity slice. arc consumes the seam by emitting nested map/fold `sub_plan`s from its `derive_initial_plan` shadow, migrating per-member bodies to dispatched capacities, and advancing `arc_plan.SOLVE_TARGET_DS` into per-stage sub-targets (arc's own pending work; the seam is inert until then, like L5 Steps 1-4 pre-Step-5).
