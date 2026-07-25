# L5 Step 5 CONFIRMED — execution.run → execute_pipeline (the solve grounds + persists)

**Work item:** `confirmation_docs/CORE_WORKITEM_TASK_INTO_L5.md` — the out-of-CR **Step 5**,
the only remaining piece and the true end-to-end blocker for `arc solve task 7`. Steps 1-4
(the L5 umbrella CR + the capacity-persist CR) built the capacity writer + Slice-B persist +
the knowledge writer, all **inert in prod**; Step 5 wires the solve path to fire them.
**Branch:** `feat/l5-step5-solve-execution` (off `main` after Slice 3).
**Gate:** full containerized run (Linux, live FalkorDB, ~35m) = **4307 passed / 12 skipped /
1 xpassed / 1 failed**, where the single failure was a **test-only literal** (a hard-coded
`"datastate_instance_type"` instead of the `PROP_DATASTATE_INSTANCE_TYPE` = `"datastate_type"`
constant — grounding itself was correct, the run graph + nodes were created). Test-only fix →
targeted re-run **8 passed / 0 failed**; source unchanged, so the effective full gate is
**4308 / 12 skip / 1 xpass / 0 fail** (baseline 4300 Slice 3 + 8 new; 0 regressions).
**core_version:** stays `phase50` (L4/L5-side code; no core-package / role / category change).

## What shipped (5 files edited, 1 new test file)

- **`mindsos_intelligence/phase_1.py`** — Step 5.1 (subsumes `CORE_CR_PHASE1_RESOLVED_REFERENCE`):
  `Phase1Result.resolved_reference` (default `None`), populated in `run()` from
  `InterpretationResult.resolved_reference`. Byte-identical when absent.
- **`mindsos_intelligence/plan_construction.py`** — Step 5.1 + 5.2: `build()` gains a
  keyword-only `resolved_reference=` that rides the already-declared `DS_MAPPING_RESULT`
  value dict (no new declared input → strict `_validate_inputs` untouched; the v0 body ignores
  it). The planner output is **no longer discarded**: `_read_solve_target` reads
  `plan_out["solve_target"]` = `{start_datastate, target_datastate}` onto a new
  `PlanResult.solve_target` (tolerant → `None` for v0 / any plan not naming both endpoints).
- **`mindsos_intelligence/execution.py`** — Step 5.3: `run()` gains a **real solve mode**.
  When the plan names a `solve_target` AND the orchestrator supplies `mm` + a seed, it
  `find_pipeline`s the leaf (Local view first, Global fallback — arc's solve caps are Local)
  and runs `execute_pipeline(mm=…, pipeline_run_ref="pipelinerun:<scope>:<leaf>:<attempt>")`,
  grounding the resolved task into `capacity_mm` (the seeded start IS the `raw_task` DAG root;
  each invocation adds its grounding DAG), emitting a real StepExecutionRecord per capacity
  step, and collecting the per-run graph. Otherwise the byte-identical Phase-47 **notional**
  record. A fresh per-run ref per (leaf, replan attempt) preserves Slice-A isolation.
- **`mindsos_intelligence/pipeline_execution.py`** — Step 5.3 (D-4): exposes the run's grounding
  graph on `PipelineExecutionResult.capacity_graph` (so the solve caller can persist it without
  re-reaching into the writer), and makes start-input seeding **idempotent** (a pre-indexed
  start is not re-minted). No-MM / submind / interpret paths stay byte-identical.
- **`mindsos_intelligence/orchestrator.py`** — Step 5.3 + 5.4: hoists the task-unique `scope`
  (drives the capacity run's `task_id`/`run_ref` so a task with no explicit `task_id` still
  grounds into an isolated graph); threads `resolved_reference` into Phase 2; builds the solve
  seed `{start_datastate: resolved_reference}`; threads `mm`/`run_scope`/`solve_seed`/
  `capacity_graphs`/`run_attempt` into `execution.run`; and passes the collected
  `capacity_graphs` to `_consolidate` → `consolidate_task(capacity_graphs=…)`, making Slice-B
  persist **non-inert** (`capacity_root_ref` lands on the Episode).
- **`tests/phase_48/test_step5_solve_execution.py`** — NEW, 8 tests: real solve grounds
  `capacity_mm` (raw_task + answer DataStateInstances + a CapacityInstance wired by
  CONSUMES/PRODUCES) + per-run graph collected + real (not notional) step records; notional
  fallback when no solve_target (capacity_mm untouched); `plan_construction` reads `solve_target`
  + threads `resolved_reference` in the payload; v0-shaped plan → `solve_target=None`;
  `execute_pipeline` exposes `capacity_graph` (and `None` with no MM); full `run_lifecycle`
  grounds the solve into `capacity_mm`; full `run_lifecycle` persists → Episode
  `capacity_root_ref` non-null (fake persister); v0 lifecycle unchanged (no capacity grounding).

## Decisions enacted (agreed with HA before build)

1. **Step 5 subsumes 3.1** (the standalone Phase-1 CR). 3.1 alone is inert; folded in.
2. **D-2 = A** — the leaf milestone names the solve target; core reads `solve_target` from the
   planner output. Core stays generic (L4 = substrate only); the brain's `derive_initial_plan`
   names the endpoints. Single-leaf scope at v1; multi-leaf target routing rides real
   decomposition (WSD), deferred.
3. **D-3 = defer the provenance XRef (5.5).** No `link_provenance` call / distinct `raw_task`
   root minted yet: the **seeded start input already lands `raw_task` in `capacity_mm`** as the
   grounding-DAG root, so acceptance holds. 5.5 is a clean add-on once the arc knowledge-target
   IRI source is settled (arc3 = `None`).

## Posture + follow-ups (honest status)

- **Per-DataState `encode` hints are a brain follow-up (PB-1).** `consolidate_task` is threaded
  `capacity_graphs` but **no `capacity_encoders`** (core has none); with none supplied every
  grounded value must already be codec-safe (primitive/dict/list) or `persist_capacity_mm`
  fails loud. The new tests use codec-safe values; a real brain whose solve produces domain
  objects must supply encoders.
- **`arc solve task 7` end-to-end depends on a brain change.** For the solver to actually run,
  arc's Local `derive_initial_plan` must emit `solve_target` in its plan output. That is an
  arc-brain edit (joint-chat rule: brains change from their own chat), so the **core machinery
  is gate-proven** by the new tests, but the live `arc solve task 7` is gated on arc emitting
  `solve_target`. Surfaced as a finding, not silently accepted.
- **Finder is single-view (Local OR Global).** `execution.run` tries Local then Global; a solve
  target reachable in neither raises `PipelineNotFoundError` (fail-loud — no dishonest
  "succeeded"). Mapping an unfindable solve to a `dont_know` verdict is a later refinement.

## Pair-exec

Cowork authored the 6 files → `device_commit_files` to the Mac tree; Mac commits + pushes the
branch; Linux fresh-clone gate authoritative (see `pair-execution-workflow`, `ship-env-invariants`).
STATE.recent entry pending the squash SHA (Mac-side idempotent script).
