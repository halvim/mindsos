# CORE CR / ADR-DRAFT — Lifecycle iteration over collections (map/fold plan primitive)

**Status:** Slice 1a SHIPPED (gate-green on `feat/collection-iteration-slice-1a` @ `9bdd026`, 4311 passed / 0 failed; see `COLLECTION_ITERATION_SLICE_1A_CONFIRMED.md`) — NOT merged. Slices 1b/2/3 designed; this doc is their proposal. ADR number to be assigned (latest Accepted = 0201).
**Date:** 2026-07-25
**Layer:** L4/L5 (lifecycle). `core_version` unchanged (L4/L5-side; no core-package / role / category change).
**Amends/relates:** ADR-0171 (six-phase lifecycle), ADR-0199 (collection/member, PRESERVED), L5 Step 5 (`L5_STEP5_CONFIRMED.md`).
**Scope of this doc:** the COMMON lifecycle seam only. No arc-side change requested here; a compliance note for arc is at the end.

---

## Problem

`run_lifecycle`'s solve path runs one `find_pipeline(start → target)` and one `execute_pipeline` per leaf, with a single plan-global `solve_target` and a single `solve_seed` applied identically to every leaf (`execution.py:57-80,106-128`; `orchestrator.py:224-241`). A real consumer's solve spans a **collection**: arc reasons across all grids / demo-pairs / objects of a task. The finder deliberately never bridges a collection DataState to its member (ADR-0199; distinct IRIs), so no single pipeline can walk `raw_task → raw_grids(collection) → raw_grid(member) → …`. Today such a solve raises `PipelineNotFoundError` — arc's reason half is hard-blocked here.

## Decision

Add a **general, composable map/fold primitive** to the lifecycle: the plan may declare that a stage is a **map** over a collection DataState (run a uniform sub-plan per member) followed by a **fold** (dispatch an L3 reducer over the members' outputs). Cardinality is filled at execution time when the collection value is known; the **shape** lives in the plan so the run is inspectable ("know the pieces").

**Bound (binding):** a map applies ONE uniform sub-plan to all members. No conditionals, no while-loops, no dynamic goals, no per-member-different plans. This is map + fold + nesting — not a workflow engine.

### Layer split (binding)
- **L3 (cognition):** the fold's **reducer** is an ordinary capacity (arc already ships `conclude_variance`, `agrees_across_demos`, `identify_roles`). The per-member work is ordinary capacities the finder composes.
- **L4 (control/substrate):** the **fan-out, the all-or-nothing barrier, the bounded retry, and the value threading** are lifecycle control. They are NOT capacities (would break the "no capacity calls another / no higher-order dispatcher" invariant and the capacities-are-cognition principle).

## Why not the alternatives (recorded)
- **Collection-aware finder (CR option C):** rejected — contradicts ADR-0199 (finder fan-out = the dropped C2, "conflates composition with iteration"). Preserved, not reopened.
- **Plan-time enumeration of members (CR option B, pure form):** impossible — member count is only known after the collection is fetched at execution time; plan construction (`plan_construction._decompose_recursive`, `decompose` fed `{}`) cannot enumerate them. Resolved by planning the *shape* and expanding *cardinality* at runtime.
- **Black-box arc capacity (`raw_task → solution`, internal loop):** rejected — zero core change but L5 sees one opaque invocation; no per-member grounding/audit, defeats the L5 value proposition.

---

## The gap this must close first (verified)

There is **no cross-milestone value threading today.** `execution.run` runs each leaf's pipeline in its own blackboard seeded from the same `solve_seed` and **discards `result.outputs`** (keeps only the grounding graph). `execute_pipeline` is one pipeline, one pass, one value per DataState IRI (`pipeline_execution.py:116,155-206`). The MM read handle (`mm_handle` = `MMResolver`, `mm_resolver.py`) reads **long-term L2 knowledge** (ontology/episodic, pinned), not the run's working values, and is inert in prod. A plan-level map/fold spans stages (produce collection → fan out → fold) that must hand values to each other, so this must be built before any fan-out.

**Fix:** a **run-scoped shared blackboard** threaded across milestones, created fresh at the top of each `execution.run` (attempt-scoped), seeded from `solve_seed`, read/written by every stage, discarded on return. Capacity_mm grounding still happens for audit; live value-threading rides this in-memory store. No capacity_mm read surface needed.

**Replan interaction (verified clean):** `replan_check.check` and `sufficient_predicate.evaluate` dispatch with empty state (they read the dispatcher/MM, not any blackboard); `invalidate_at_and_below` only clears `task_run.pipeline_runs` (`replan_check.py:32-43`). Because the shared blackboard is attempt-scoped, a replan re-runs from a clean blackboard + fresh grounding refs (`run_attempt++`) — no stale reads, no double-seed.

---

## Contracts

### Map node
Names: the collection DataState (its value already on the blackboard from an upstream stage), the member DataState (via the `member_ds` pointer, ADR-0199), and the per-member sub-target. Execution, when it reaches the node: read the collection from the shared blackboard, unpack to ordered members, and for each member run `find_pipeline(member → sub_target)` + `execute_pipeline` in an isolated sub-blackboard seeded with the member value. One fresh per-run ref per member (`pipelinerun:{scope}:{path}:{attempt}`; the path nests for Slice 2) → isolated grounding graph per member (reuses Slice-A isolation).

### Fold node (barrier + aggregate)
Depends on ALL members of its map. Members run in the collection's order; the fold receives their outputs in that order. Behavior:
- **∀-abort:** if any member sub-run returns **success = false** (a load/compute failure that survives retry), abort the map immediately (skip remaining members), the fold does not run, the task aborts. Keys on the executor **success flag**, not the produced value.
- **Success (incl. "disagree"):** if every member sub-run succeeds, the fold dispatches its L3 reducer over the ordered member outputs and writes the aggregate to the shared blackboard for downstream stages. A reducer that concludes "no consistent rule" is a legitimate `dont_know` result — NOT an abort.
- Replaces the unwired `planning_v0.aggregate_outputs` stub (registered but never called anywhere in `mindsos_intelligence/`).

### Bounded retry (member load failure)
On a member sub-run failure: retry up to a hard cap. **Cap = 2 total attempts (initial + 1 retry)** (owner's call), exposed as a named constant `MEMBER_RETRY_CAP` (mirrors `DEFAULT_PER_TASK_REPLAN_BUDGET`; trivially tunable). Accept the first attempt that executes cleanly. If still failing at the cap, ∀-abort. Compares the success flag only. Persist only the accepted attempt's grounding graph (discard rejected attempts; each attempt already gets a fresh ref). No unbounded retry.

---

## Slices

- **1a — cross-milestone value bus. ✅ SHIPPED** (`9bdd026`, gate 4311/0; `COLLECTION_ITERATION_SLICE_1A_CONFIRMED.md`). Run-scoped, attempt-scoped shared blackboard threaded across milestones + additive `PlanResult.leaf_targets`. Proof gate: a 2-stage linear plan (stage A produces `raw_grids`, stage B consumes it). Byte-identical for the single-leaf path.
- **1b — map + fold + barrier + bounded retry.** Map/fold milestone kinds in the plan model; executor fan-out + ∀-abort barrier + retry; per-member grounding; fold dispatches an L3 reducer over ordered outputs. Sequential members. Single (non-nested) level.
- **2 — nesting. ✅ SHIPPED** (`41d2110`, PR #72, gate 4331 passed / 0 failed; `COLLECTION_ITERATION_SLICE_2_CONFIRMED.md`). A map's sub-plan may itself contain a map/fold (objects within grids) via an optional `sub_plan` on the map node; the per-member run-ref became a path (`pipelinerun:{scope}:{ref_path}[:m{i}]…`) so nested grounding stays isolated and the set of per-run graphs is a locatable tree. **Cross-stage grounding continuity was NOT included** — verified not additive (see the 1a sub-item below), deferred to its own slice.
- **3 — per-member replan/diagnosis (ADDRESSING). ✅ SHIPPED** (`2ad8080`, PR #75, gate 4335 passed / 0 failed; `COLLECTION_ITERATION_SLICE_3_CONFIRMED.md`). `ReplanVerdict` gains optional *advisory* `replan_level` (reserved `"map"` / `"plan_subtree"`, `replan_check.py:19`) + `target_ref` (the Slice-2 member ref-path); the orchestrator records the target on the `ReplanRecord` (the pre-existing `replan_milestone_ref` slot; recorded `replan_level` stays `"pipeline"` = the actual whole-pipeline action, so a full clear is never mislabeled) and feeds it to Phase-6 diagnosis (member-scoped `BlameVerdict.milestone_ref`). Replan **execution** stays whole-pipeline; v0/1a/1b/2 byte-identical. **Targeted RE-EXECUTION deferred (Slice 3b)** — not additive: it reverses Slice-1a's attempt-scoped blackboard, and a map emits ONE `PipelineRun` for all members (no per-member chain artifact to invalidate) — same class as the cross-stage-continuity slice, best done together with owner sign-off.
- **3b — targeted RE-EXECUTION (option A). ✅ SHIPPED** (`b3bae74`, PR #83, gate 4351 passed / 0 failed; `COLLECTION_ITERATION_SLICE_3B_CONFIRMED.md`). The orchestrator now **acts** on a Slice-3 target: when the verdict names a re-runnable **top-level flat map** member (reserved `"map"`/`"plan_subtree"` + a resolvable ref-path), it **retains the blackboard across the replan loop** and re-runs only that member (`execution.run(targeted=(map_idx,member_idx))`), reusing the completed siblings + their grounding; `invalidate_at_and_below(at_index)` keeps the prefix (map + fold + downstream cleared); `resolve_member_target` gates to a bare `{leaf_idx}:m{member_idx}` (a full `pipelinerun:` advisory ref or a nested path → whole-pipeline, byte-identical to Slice 3). **Option A** (owner-approved): reuses the shipped Slice-2 grounding ref-path — **no** promotion of members to first-class chain PipelineRuns. Additive-inert (`execution.run` unchanged when no target is named). Verified at the branch base: **G1** the replan-after-successful-map trigger exists but is inert (v0 `should_replan`/`sufficient` stubs); **G2** the member axis lives only in the grounding ref-path (= exactly Slice-3's `target_ref`), so option A needs no run-list change; **G3** intergraph-edge persistence is unbuilt. **Deferred to one combined later slice** (gated on a live replan-after-map trigger): option **B** (members → first-class PipelineRuns; reverses the Slice-2 flat run-list) + **cross-stage grounding continuity** (reverses the Slice-A per-run-graph model). Slice-3b's retry/keep-siblings/selective-invalidate machinery is ~80% reusable toward B.

## Locked decisions (owner, 2026-07-25)
1. **Members run sequentially** in v1 (deterministic grounding). Parallel is a later option.
2. **Retry cap = 2 total attempts** (`MEMBER_RETRY_CAP`, tunable).
3. **arc's `derive_initial_plan` shadow emits the map/fold shape.** Core provides only the milestone kinds + executor + value bus; arc populates the specific structure (which collections, which reducers). No core planner logic learns arc's shape.

## Slice 1a — implementation spec (value bus)

**Goal:** thread DataState values across milestones within one attempt, so a downstream stage can consume what an upstream stage produced. Proves the prerequisite before any fan-out. No map/fold yet.

**Seam (all in `mindsos_intelligence/execution.py`; `orchestrator.py` unchanged):**
- `execution.run` creates one `blackboard: dict` at entry, initialized `dict(solve_seed or {})`. Attempt-scoped: created per `run` call, discarded on return → replan re-enters clean.
- Per milestone, seed that stage's `execute_pipeline` from the blackboard **filtered to the stage pipeline's `start_datastates`**: `{ds: blackboard[ds] for ds in pipeline.start_datastates if ds in blackboard}`. (Do NOT pass the whole blackboard — `execute_pipeline` seeds every initial input as a grounding root (`pipeline_execution.py:135-141`); passing unrelated values would mint them as false roots.)
- After the stage, merge its outputs: `blackboard.update(result.outputs)`. Today `result.outputs` is discarded (`execution.py` keeps only `capacity_graph`); this is the change.

**Inertness property:** with the current single-leaf plan, the blackboard is initialized to `solve_seed`, the sole leaf seeds from it (== `dict(solve_seed)` today) and merges outputs no one reads → **byte-identical outcome**. The change only activates when a plan has >1 stage. (Same additive-inertness basis as L5 Step 5.)

**Proof plan (the gate):** a 2-stage linear test plan — stage A `{canonical_ref → raw_grids}`, stage B `{raw_grids → <sink>}` — where B's start is produced only by A. Assert: B runs (not `PipelineNotFoundError` for a missing start), B's dispatched capacity received A's `raw_grids` value, and a replan re-runs both stages from a clean blackboard. Today this test fails (B's start never arrives); Slice 1a makes it pass.

**Remaining sub-item (decide in 1a, does not block starting):** cross-stage *grounding* continuity. Value threading is in-memory; each stage still grounds into its own per-run graph, so B's `raw_grids` seeds as a fresh root in B's graph rather than linking to A's output instance. Options: (i) accept independent per-stage graphs for 1a (simplest; provenance link deferred), or (ii) link B's seeded start to A's produced instance via the run-ref index. Proposed: (i) for 1a, revisit under Slice 2's run-ref path. **UPDATE (Slice 2 shipped 2026-07-25):** option (ii) is NOT achievable additively — `execute_pipeline` builds a fresh per-`(task_id, pipeline_run_ref)` `CapacityMMWriter` (one isolated graph per run, empty index) and PRODUCES/CONSUMES are intra-graph (Slice A, to sidestep intergraph-edge persistence; the persister takes one per-run graph whole). Linking a consumer's seeded start to the producer's instance needs an edge across two run-graphs — either an intergraph edge (lives in neither graph, so its persistence is unbuilt) or sharing one graph across sequential stages (rekey on task+attempt, which collides with the map's per-member isolation) — both reverse a shipped Slice-A decision and are not byte-identical. Continuity is therefore its OWN slice; Slice 2 delivered the isolated, locatable provenance tree (the ref-path), not the connected cross-stage DAG.

---

## What arc must do to comply (handoff, no action requested yet)
1. Emit a structured plan from arc's `derive_initial_plan` shadow: map nodes over `raw_grids` / `raw_pairs` / `objects`, with fold nodes naming arc's reducers (`conclude_variance`, `agrees_across_demos`, …).
2. Migrate the per-member bodies from inline compute (`arc_solver.py`) to dispatched capacities — the seam grounds nothing until arc runs through `invoke` (arc's own "pending decision"). Until then the seam is inert (like L5 Steps 1–4 pre-Step-5).
3. Advance `arc_plan.SOLVE_TARGET_DS` past `raw_task` into the reasoning targets, now expressible as per-stage sub-targets.
