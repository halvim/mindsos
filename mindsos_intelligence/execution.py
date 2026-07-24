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

**Cross-milestone value bus (collection-iteration Slice 1a).**

The run holds one attempt-scoped ``blackboard`` — created here at the top of
``run`` and discarded when it returns — that threads DataState *values* across
milestones. A leaf seeds its pipeline from the blackboard (filtered to the
pipeline's ``start_datastates``) and merges its outputs back, so a downstream
stage can consume what an upstream stage produced (e.g. ``raw_task -> raw_grids``
then ``raw_grids -> ...``). Because the blackboard is created per ``run`` call,
a replan (a fresh ``run`` at the next ``run_attempt``) re-enters from clean
state — no stale reads. ``capacity_mm`` still grounds each leaf's run for audit;
the blackboard only carries the live values between stages.

A multi-stage plan names per-leaf endpoints via ``PlanResult.leaf_targets``
(``{leaf_ref: {start_datastate, target_datastate}}``); a leaf with no entry
falls back to the plan-global ``solve_target``. With a single-leaf plan and no
``leaf_targets`` (today's v0 / Step-5 path) the behaviour is byte-identical: the
sole leaf seeds from the blackboard initialised to ``solve_seed`` and merges
outputs no one reads.

MSUR + SCMS Plan/Milestone orchestration hooks (WSD) are still absent; the loop
stays sibling-sequential v1. Per-member map/fold fan-out (run a sub-pipeline per
collection member, then fold) is the next slice (1b) and is NOT here — Slice 1a
only threads values across whatever leaves the plan already names.
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
    to the resolved-task value (Phase-1 ``resolved_reference``) and seeds the
    run-scoped blackboard. When ``mm``/``solve_seed`` are absent — or the plan
    names neither ``solve_target`` nor a ``leaf_targets`` entry for a leaf — that
    leaf falls back to the notional record. ``capacity_graphs`` (when a list is
    passed) collects each real run's ``capacity_mm`` grounding graph for
    consolidation persistence. ``run_attempt`` (the orchestrator's replan
    counter) makes each replan re-run's per-run ref fresh, so a re-dispatch
    grounds an isolated graph instead of overwriting the prior attempt's
    (Slice A isolation)."""
    pipeline_run_refs: List[str] = []
    solve_target = getattr(plan_result, "solve_target", None)
    leaf_targets = getattr(plan_result, "leaf_targets", None) or {}
    # Real-solve mode is active when the orchestrator supplies the MM + seed and
    # the plan names at least one endpoint (a plan-global ``solve_target`` or any
    # per-leaf entry). v0 / no-endpoint plans stay on the notional path.
    real_mode = (
        mm is not None
        and solve_seed is not None
        and (solve_target is not None or bool(leaf_targets))
    )
    # Slice 1a — one attempt-scoped blackboard threaded across milestones. Fresh
    # per ``run`` call (so replan re-enters clean); seeded from ``solve_seed``.
    blackboard: dict = dict(solve_seed or {})
    for leaf_idx, leaf_ref in enumerate(plan_result.leaf_milestone_refs):
        pipeline_ref = plan_result.pipeline_refs[leaf_ref]
        pr = writer.emit_pipeline_run(pipeline_ref, leaf_ref, task_run.iri)
        endpoints = leaf_targets.get(leaf_ref) or solve_target
        if real_mode and endpoints is not None:
            outputs = _run_leaf_pipeline(
                dispatcher, writer, pr, leaf_ref, endpoints, blackboard,
                mm, run_scope or task_run.iri, leaf_idx, run_attempt,
                capacity_graphs,
            )
            # Thread this stage's produced values to downstream stages.
            blackboard.update(outputs)
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
    dispatcher, writer, pr, leaf_ref, endpoints, blackboard,
    mm, task_id: str, leaf_idx: int, run_attempt: int,
    capacity_graphs: Optional[list],
) -> dict:
    """Find + run the real leaf pipeline; ground it into ``capacity_mm``, collect
    its per-run graph, and return its outputs (for the caller to thread onto the
    run blackboard). Local imports keep this module's import graph light and
    cycle-free (``pipeline_execution`` reaches ``capacity_mm_writer`` → ``mm`` →
    core, none of which import ``execution``)."""
    from mindsos_capacity.exceptions import PipelineNotFoundError
    from mindsos_capacity.pipeline import find_pipeline

    from .pipeline_execution import execute_pipeline

    start = endpoints["start_datastate"]
    target = endpoints["target_datastate"]
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
    # Slice 1a — seed only the values the pipeline declares as starts, drawn from
    # the shared blackboard (an upstream stage may have produced them). Filtering
    # to ``start_datastates`` keeps ``execute_pipeline`` from minting unrelated
    # blackboard values as grounding roots (it seeds every initial input).
    seed = {
        ds: blackboard[ds]
        for ds in pipeline.start_datastates
        if ds in blackboard
    }
    run_ref = f"pipelinerun:{task_id}:{leaf_idx}:{run_attempt}"
    result = execute_pipeline(
        dispatcher,
        pipeline,
        seed,
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
    return dict(result.outputs)


__all__ = ["run"]
