# Collection-iteration Slice 1b CONFIRMED — map/fold fan-out + all-or-nothing barrier + bounded retry

**Status:** BUILT + GATE-GREEN on `feat/collection-iteration-slice-1b` (commit `db4d0dd`) — NOT merged (PR pending).
**Gate:** full containerized run (Linux, live FalkorDB, 2026-07-25) = **4316 passed / 12 skipped / 1 xpassed / 0 failed**, 32m24s. `main` baseline + 4 new (the Slice-1b map/fold tests); 0 regressions.
**Targeted pre-gate:** `pytest tests/phase_48/test_slice1b_map_fold.py tests/phase_48/test_slice1a_value_bus.py tests/phase_48/test_step5_solve_execution.py` = 14 passed (4 new + 2 Slice-1a + 8 Step-5 regression).
**core_version:** stays `phase50` (L4/L5-side; no core-package / role / category change).
**CR / design:** `confirmation_docs/CORE_CR_COLLECTION_ITERATION.md`. Relates ADR-0171 (lifecycle); ADR-0199 PRESERVED (collection/member typing consumed, finder never bridges).

## What this slice is

The map/fold plan primitive, built on the Slice-1a value bus. A `map` milestone fans a uniform sub-pipeline out over the ordered members of a collection DataState (ADR-0199 — "L4 owns the unpack loop"), and a `fold` milestone dispatches an L3 reducer over the members' ordered outputs. The fan-out, the all-or-nothing barrier, the bounded retry, and the value threading are lifecycle control (L4); the per-member work and the reducer are ordinary capacities (L3) — the layer split the CR made binding. This is what lets a real consumer (arc) reason across a whole collection (all grids / demo-pairs / objects) instead of a single leaf. No nesting yet (Slice 2); members run sequentially (v1).

## What shipped (3 edited, 1 new test)

- **`mindsos_intelligence/execution.py`** — the run loop gains map/fold branches keyed on a milestone's spec `kind`, alongside the unchanged leaf/notional paths:
  - `_run_map_milestone` — reads the ordered collection from the shared blackboard, and for each member (sequential) runs `find_pipeline(member_ds -> sub_target)` + `execute_pipeline` in an isolated sub-blackboard seeded with just the member value, under a fresh per-member run-ref `pipelinerun:{scope}:{leaf_idx}:m{i}:{attempt}:r{retry}` (isolated grounding graph per member). **Bounded retry** to `MEMBER_RETRY_CAP = 2` (accept the first `success=True` attempt; only its `capacity_graph` is persisted — rejected attempts leave nothing in `capacity_graphs`). **All-or-nothing barrier**: a member still failing at the cap raises `MemberAbortError` (remaining members skipped; the fold never runs). On success, writes the ordered list of members' `sub_target` outputs to `blackboard[out_ds]`.
  - `_run_member_pipeline` — a pure find+execute for one member (no writer / graph side effects, so the map owns accept/reject and discards rejected attempts). Returns `(PipelineExecutionResult, pipeline)`.
  - `_run_fold_milestone` — dispatches the plan-named L3 `reducer_iri` over the ordered member outputs on the blackboard (`in_ds` = the map's `out_ds`) and merges the aggregate back. This is the real aggregation the registered-but-unwired `planning_v0.aggregate_outputs` stub only stood in for. A reducer concluding "no consistent rule" is a legitimate value (→ `dont_know` via the existing `sufficient_predicate` path), NOT an abort.
  - `MEMBER_RETRY_CAP` + `MemberAbortError` are module-level (exported); `real_mode` now also activates on a plan carrying `milestone_specs`.
- **`mindsos_intelligence/plan_construction.py`** — additive `PlanResult.milestone_specs: Optional[Dict[str, Dict[str, Any]]] = None`, mapping a milestone ref to a `map` (`{kind, collection_ds, member_ds, sub_target, out_ds}`) or `fold` (`{kind, reducer_iri, in_ds}`) descriptor. A ref absent from the map is a plain leaf. The consumer's planner emits the shape (arc's `derive_initial_plan` shadow — locked decision 3); core stays shape-agnostic. The v0 builder never sets it.
- **`mindsos_intelligence/orchestrator.py`** — the Phase 3-5 run loop catches `execution.MemberAbortError` → `task_run.status = "aborted"` → consolidate → `TaskOutcome("aborted", …)`. A member load-failure abort is distinct from a reducer `dont_know` and from a replan (it is not retried at the whole-task level).
- **`tests/phase_48/test_slice1b_map_fold.py`** (NEW, 4) — over real capacities, no Falkor: (1) map fans out over 3 members and the fold reduces their outputs **in collection order**; (2) a member that fails past the cap raises `MemberAbortError`, skips the remaining member, and the fold never runs; (3) retry-then-succeed within the cap (a member fails once then succeeds, all three fold in order); (4) a plan with no `milestone_specs` runs the plain-leaf path unchanged.

## Inertness (no regression to shipped paths)

`milestone_specs` is absent on every v0 / 1a / Step-5 plan, so `kind` is `None` and every milestone takes the existing leaf/notional branch — **byte-identical**. The map/fold branches are reachable only when a plan explicitly carries a spec (and `mm` + seed are supplied). The 8 Step-5 and 2 Slice-1a regression tests pass unchanged.

## Design decisions honored (CR §Locked decisions, owner 2026-07-25)

- **Members sequential (v1)** — deterministic grounding order; the fold receives outputs in the collection's order (asserted).
- **Retry cap = 2 total attempts** — named `MEMBER_RETRY_CAP`, tunable; keys on the executor success flag only.
- **Fold reducer = L3 capacity; fan-out/barrier/retry/threading = L4 control** — the reducer is dispatched via the ordinary `dispatcher.dispatch` path; the control lives in `execution.py`, not in any capacity (preserves "no capacity calls another / no higher-order dispatcher").
- **Consumer emits the shape** — core added only the milestone kinds + executor + the run-ref path; no core planner logic learns arc's structure.

## Verified substrate facts

- A raising capacity body is enveloped by `mindsos_capacity.runtime.invoke` as `InvocationResult(success=False)` (ADR-0072 §amendment-1), which `execute_pipeline` returns as `success=False` — the deterministic member-failure signal the retry/abort tests use (no exception escapes the sub-run).
- Collection value contract: a collection DataState's value on the blackboard is an ordered Python list of member values; the map unpacks it positionally (`member_ds` from ADR-0199 typing). `DataState(collection=True, member_ds=…)` coherence is validated at registration (`datastate.py:214-227`).
- Per-member grounding isolation reuses the Slice-A fresh-ref mechanism: each member attempt gets a distinct `pipelinerun:` ref, so `execute_pipeline`'s `CapacityMMWriter` mints an isolated graph per member (and per retry); consolidation persists only accepted attempts.

## Abort semantics (recorded)

`MemberAbortError` is the ∀-abort signal, raised from the map and caught once in the orchestrator. It is deliberately NOT a replan (a member load failure exhausted its own retry budget) and NOT a `dont_know` (which is a reducer's successful verdict over member outputs). A reducer that itself errors marks the fold PR `failed` without merging an aggregate; a reducer that succeeds with a "no rule" value flows to Phase 6 via `sufficient_predicate` as today.

## Open items (deferred within the CR)

- **Nesting (Slice 2)** — a map's sub-plan may itself contain a map/fold; the per-member run-ref becomes a path (`{scope}:{path}:{attempt}`) so grounding stays isolated and the provenance tree is readable. Also picks up Slice 1a's deferred cross-stage grounding continuity.
- **Per-member replan/diagnosis (Slice 3)** — point replan at a specific member via the reserved `"map"` / `"plan_subtree"` REPLAN_LEVELS (`replan_check.py:19`).
- **Parallel members** — sequential in v1 by decision; parallel fan-out is a later option.

## Next

Slice 2 (nesting) — then Slice 3 (per-member replan). arc consumes the seam by: emitting map/fold nodes from its `derive_initial_plan` shadow, migrating per-member bodies from inline compute to dispatched capacities, and advancing `arc_plan.SOLVE_TARGET_DS` past `raw_task` into per-stage sub-targets (arc's own pending work; the seam is inert until then, like L5 Steps 1-4 pre-Step-5).
