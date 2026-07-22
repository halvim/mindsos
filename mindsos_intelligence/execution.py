"""LifecyclePhase 3-5 — execution (DFS Milestone order, ADR-0171).

Walks the Plan's leaf Milestones in DFS order; per leaf emits a
PipelineRun and runs the leaf Pipeline.

**Two modes (out-of-CR Step 5).**

* *Notional (v0 / no solve target).* When the plan names no ``solve_target``
  (the v0 placeholder planner, and any consumer that doesn't declare one), the
  leaf has no real pipeline to run: emit a single notional StepExecutionRecord
  so the PipelineRun has provenance, and mark it completed. This is the
  byte-identical Phase-47 behaviour.
* *Real solve.* When the plan names ``solve_target`` (``{start_datastate,
  target_datastate}``) AND an ``mm`` + seed are supplied by the orchestrator,
  the leaf runs for real: the bipartite ``find_pipeline`` (ADR-0156) composes a
  Pipeline from the currently-registered capacities, and ``execute_pipeline``
  runs it — grounding the run into ``capacity_mm`` (the resolved task lands as
  the seeded start DataStateInstance; each invocation adds its grounding DAG)
  and threading the per-run graph out for Slice-B persistence. This is what
  makes the L5 capacity writer + persist non-inert (Steps 1-4 built them inert).

MSUR + SCMS Plan/Milestone orchestration hooks (WSD) are still absent; the loop
stays sibling-sequential v1. Multi-leaf target routing (each leaf its own
target) rides real decomposition and is deferred — at v1 the plan is
single-leaf, so the one ``solve_target`` applies to the sole leaf.
"""

from __future__ import annotations

from typing import Any, List, Optional


def run(
    dispatcher,
    writer,
    plan_result,
    task_run,
    *,
    mm: Any = None,
    run_scope: Optional[str] = None,
    solve_seed: Optional[dict] = None,
    capacity_graphs: Optional[list] = None,
    run_attempt: int = 0,
) -> List[str]:
    """Run each leaf Pipeline; return the PipelineRun IRIs.

    ``mm`` / ``run_scope`` / ``solve_seed`` are supplied by the orchestrator on
    the solve path (Step 5). ``solve_seed`` maps the plan's ``start_datastate``
    to the resolved-task value (Phase-1 ``resolved_reference``). When any is
    absent — or the plan names no ``solve_target`` — the leaf falls back to the
    notional record. ``capacity_graphs`` (when a list is passed) collects each
    real run's ``capacity_mm`` grounding graph for consolidation persistence.
    ``run_attempt`` (the orchestrator's replan counter) makes each replan
    re-run's per-run ref fresh, so a re-dispatch grounds an isolated graph
    instead of overwriting the prior attempt's (Slice A isolation)."""
    pipeline_run_refs: List[str] = []
    solve_target = getattr(plan_result, "solve_target", None)
    real = solve_target is not None and mm is not None and solve_seed is not None
    for leaf_idx, leaf_ref in enumerate(plan_result.leaf_milestone_refs):
        pipeline_ref = plan_result.pipeline_refs[leaf_ref]
        pr = writer.emit_pipeline_run(pipeline_ref, leaf_ref, task_run.iri)
        if real:
            _run_leaf_pipeline(
                dispatcher, writer, pr, leaf_ref, solve_target, solve_seed,
                mm, run_scope or task_run.iri, leaf_idx, run_attempt,
                capacity_graphs,
            )
        else:
            # Notional step record (no real capacity steps at v0) — unchanged
            # Phase-47 behaviour.
            writer.emit_step_execution_record(
                pipeline_ref,
                pipeline_run_ref=pr.iri,
                milestone_ref=leaf_ref,
                confidence=1.0,
            )
            pr.status = "completed"
        pipeline_run_refs.append(pr.iri)
        task_run.pipeline_runs.append(pr.iri)
    return pipeline_run_refs


def _run_leaf_pipeline(
    dispatcher, writer, pr, leaf_ref, solve_target, solve_seed,
    mm, task_id: str, leaf_idx: int, run_attempt: int,
    capacity_graphs: Optional[list],
) -> None:
    """Find + run the real leaf pipeline; ground it into ``capacity_mm`` and
    collect its per-run graph. Local imports keep this module's import graph
    light and cycle-free (``pipeline_execution`` reaches ``capacity_mm_writer``
    → ``mm`` → core, none of which import ``execution``)."""
    from mindsos_capacity.exceptions import PipelineNotFoundError
    from mindsos_capacity.pipeline import find_pipeline

    from .pipeline_execution import execute_pipeline

    start = solve_target["start_datastate"]
    target = solve_target["target_datastate"]
    # Compose the pipeline from the currently-registered capacities (the finder
    # is role-blind; L4 binds operands at dispatch — ADR-0071/0156). The finder
    # sees a single view (Local OR Global, never unioned — pipeline.py
    # ``_view_for``); a consumer's solve caps are typically Local (arc), so try
    # the session's Local view first and fall back to Global. A fresh per-run
    # ref per leaf gives each run its own isolated grounding graph (Slice A:
    # replan / concurrent isolation).
    try:
        pipeline = find_pipeline(
            dispatcher.capacity_layer,
            session=dispatcher.session,
            start_datastate=start,
            target_datastate=target,
        )
    except PipelineNotFoundError:
        pipeline = find_pipeline(
            dispatcher.capacity_layer,
            session=None,
            start_datastate=start,
            target_datastate=target,
        )
    run_ref = f"pipelinerun:{task_id}:{leaf_idx}:{run_attempt}"
    result = execute_pipeline(
        dispatcher,
        pipeline,
        dict(solve_seed),
        task_id=task_id,
        mm=mm,
        pipeline_run_ref=run_ref,
    )
    # Real provenance: one StepExecutionRecord per executed capacity step
    # (replaces the single notional record).
    for step in getattr(pipeline, "steps", ()) or ():
        writer.emit_step_execution_record(
            step.capacity_iri,
            pipeline_run_ref=pr.iri,
            milestone_ref=leaf_ref,
            confidence=1.0 if result.success else 0.0,
        )
    pr.status = "completed" if result.success else "failed"
    if capacity_graphs is not None and result.capacity_graph is not None:
        capacity_graphs.append(result.capacity_graph)


__all__ = ["run"]
