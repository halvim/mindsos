# ADR-0172 — Amendment 1: Phase 3-5 execution wiring (out-of-CR Step 5)

**Status:** Accepted (2026-07-22). Records the out-of-CR **Step 5** of the "load the resolved
task into L5" work item (`CORE_WORKITEM_TASK_INTO_L5.md`) — making the six-phase lifecycle's
Phase 3-5 run a real pipeline so the L5 capacity writer + Slice-B persist (built inert by the
L5 umbrella CR + the capacity-persist CR) fire on the solve path. Confirm:
`confirmation_docs/L5_STEP5_CONFIRMED.md`.

## Context

The base ADR (Phase-1 five-step interpretation) and ADR-0171 (six-phase lifecycle) ran the
control flow over v0 catalogs: Phase 1 `interpret()` produced a `resolved_reference` that
`run()` dropped; Phase 2 hardcoded a single-milestone plan and discarded the planner output;
Phase 3-5 (`execution.run`) emitted a **notional** StepExecutionRecord per leaf and never called
`execute_pipeline`. So the resolved task reached nothing downstream, and the capacity/knowledge
MM writers had no non-inert caller.

## Decision (Step 5)

- **Phase 1 → 2 carry (5.1, subsumes `CORE_CR_PHASE1_RESOLVED_REFERENCE`).** `Phase1Result`
  gains `resolved_reference` (default `None`), populated in `run()` and threaded through
  `orchestrator` → `plan_construction.build(resolved_reference=…)` inside the already-declared
  `DS_MAPPING_RESULT` value dict. No new declared input; the strict `_validate_inputs` contract
  and the all-v0 path are untouched.

- **Phase 2 names the solve target (5.2).** `plan_construction.build` stops discarding the
  `planning.derive_initial_plan` output; it reads `plan_out["solve_target"]` =
  `{start_datastate, target_datastate}` onto `PlanResult.solve_target`. A plan that names none
  (v0, and any plan without both endpoints) yields `None`. This is the core↔brain plan contract:
  a real consumer's planner (seeing `resolved_reference`) names the endpoints; core reads them.

- **Phase 3-5 runs for real (5.3).** When the plan names a `solve_target` and the orchestrator
  supplies the session `mm` + the solve seed, `execution.run` composes the leaf pipeline via the
  bipartite `find_pipeline` (Local view first, Global fallback) and runs it through
  `execute_pipeline(mm=…, pipeline_run_ref="pipelinerun:<scope>:<leaf>:<attempt>")` — grounding
  the resolved task into `capacity_mm` (the seeded start is the `raw_task` grounding-DAG root;
  each invocation adds its DAG) and emitting a real StepExecutionRecord per capacity step. A
  fresh per-run ref per (leaf, replan attempt) preserves the Slice-A per-run isolation.
  `execute_pipeline` exposes the run's grounding graph (`PipelineExecutionResult.capacity_graph`)
  and seeds start inputs idempotently. Absent a `solve_target`/`mm`, the byte-identical Phase-47
  notional record is kept.

- **Persist (5.4).** The orchestrator collects each run's grounding graph and threads it into
  `consolidate_task(capacity_graphs=…)`, making the reopened-DQ-8 Slice-B `capacity_mm`
  persistence non-inert: the Episode's `capacity_root_ref` now resolves to the task's
  capacity index graph. Per-DataState `encode` hints (PB-1) remain a **brain follow-up**; with
  none supplied, grounded values must already be codec-safe.

## Scope / deferrals

- **Provenance XRef deferred (5.5, D-3).** `link_provenance` is not yet called on the solve path
  (no distinct `raw_task` root minted): the seeded start already lands `raw_task` in
  `capacity_mm`, so acceptance holds. The `capacity_mm`→`knowledge_mm` XRef (ADR-0201 am-3) is a
  clean add-on once the arc knowledge-target IRI source is settled (arc3 = `None`).
- **Single-leaf scope.** Multi-leaf per-target routing rides real decomposition (WSD), deferred.
- **`arc solve task 7` e2e** additionally requires arc's Local `derive_initial_plan` to emit
  `solve_target` (a brain change); the core machinery is gate-proven independently.

## Consequences

Steps 1-4 (capacity writer, per-run persist, knowledge writer) are non-inert on the solve path:
a real solve grounds through `execute_pipeline` and the Episode persists the capacity graph.
`arc solve task 7` reaches execution once its brain names the solve target. No status flip on
the base ADR; the ADR-status gate keys by filename first-4-chars, so this prose-only amendment
coexists (base file wins the `0172` status key), matching the ADR-0201 amendment-file format.
