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

**Map / fold primitive (collection-iteration Slice 1b).**

A milestone may carry a ``PlanResult.milestone_specs`` entry marking it a **map**
or a **fold** (the consumer's planner emits the shape — locked decision 3; core
provides only the kinds + executor + value bus). A map fans a uniform
sub-pipeline out over the ordered members of a collection DataState (ADR-0199 —
L4 owns the unpack loop), sequentially (v1), each member in an isolated
sub-blackboard seeded with just the member value and under a fresh per-member
run-ref (isolated grounding). It applies bounded retry (``MEMBER_RETRY_CAP``) and
an all-or-nothing (``∀-abort``) barrier — an exhausted member raises
``MemberAbortError`` — and writes the ordered member outputs to the blackboard. A
fold dispatches an L3 reducer over that ordered list and merges the aggregate
back. A milestone with no spec is a plain leaf (the 1a path, unchanged).

MSUR + SCMS Plan/Milestone orchestration hooks (WSD) are still absent; the loop
stays sibling-sequential v1.
"""

from __future__ import annotations

from typing import Any, List, Optional

#: Slice 1b — hard cap on per-member sub-run attempts (initial + retries) inside
#: a map fan-out. Owner's call (CR §Bounded retry): 2 total attempts. A named
#: constant (mirrors ``DEFAULT_PER_TASK_REPLAN_BUDGET``), trivially tunable. A
#: member still failing (``success=False``) at the cap triggers the ∀-abort.
MEMBER_RETRY_CAP = 2


class MemberAbortError(Exception):
    """All-or-nothing abort signal (collection-iteration Slice 1b).

    Raised by a map milestone when one member's sub-run still returns
    ``success=False`` after ``MEMBER_RETRY_CAP`` attempts (a load/compute failure
    that survived retry). Remaining members are skipped and the fold never runs;
    the orchestrator catches this and aborts the task. Deliberately distinct from
    (a) a reducer concluding "no consistent rule" — a legitimate ``dont_know``
    *value*, not an abort — and (b) a replan (a member load failure is not
    retried at the whole-task level)."""

    def __init__(self, leaf_ref: str, member_index: int, message: str = ""):
        self.leaf_ref = leaf_ref
        self.member_index = member_index
        super().__init__(
            message
            or f"map {leaf_ref!r}: member {member_index} failed after "
            f"{MEMBER_RETRY_CAP} attempt(s) (all-or-nothing abort)"
        )


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
    names neither ``solve_target``, a ``leaf_targets`` entry, nor a map/fold
    ``milestone_specs`` entry — that leaf falls back to the notional record.
    ``capacity_graphs`` (when a list is passed) collects each real run's
    ``capacity_mm`` grounding graph for consolidation persistence. ``run_attempt``
    (the orchestrator's replan counter) makes each replan re-run's per-run ref
    fresh, so a re-dispatch grounds an isolated graph instead of overwriting the
    prior attempt's (Slice A isolation). A map milestone whose member exhausts
    ``MEMBER_RETRY_CAP`` raises :class:`MemberAbortError` (the orchestrator turns
    it into an aborted task)."""
    pipeline_run_refs: List[str] = []
    solve_target = getattr(plan_result, "solve_target", None)
    leaf_targets = getattr(plan_result, "leaf_targets", None) or {}
    milestone_specs = getattr(plan_result, "milestone_specs", None) or {}
    # Real-solve mode is active when the orchestrator supplies the MM + seed and
    # the plan names at least one endpoint (a plan-global ``solve_target`` or any
    # per-leaf entry) or a map/fold milestone spec (Slice 1b). v0 / no-endpoint
    # plans stay on the notional path.
    real_mode = (
        mm is not None
        and solve_seed is not None
        and (
            solve_target is not None
            or bool(leaf_targets)
            or bool(milestone_specs)
        )
    )
    # Slice 1a — one attempt-scoped blackboard threaded across milestones. Fresh
    # per ``run`` call (so replan re-enters clean); seeded from ``solve_seed``.
    blackboard: dict = dict(solve_seed or {})
    for leaf_idx, leaf_ref in enumerate(plan_result.leaf_milestone_refs):
        pipeline_ref = plan_result.pipeline_refs.get(leaf_ref)
        pr = writer.emit_pipeline_run(pipeline_ref, leaf_ref, task_run.iri)
        spec = milestone_specs.get(leaf_ref)
        kind = spec.get("kind") if spec else None
        endpoints = leaf_targets.get(leaf_ref) or solve_target
        if real_mode and kind == "map":
            # Slice 1b — fan out a uniform sub-plan over the collection's members
            # (∀-abort barrier + bounded retry inside); writes the ordered member
            # outputs to the blackboard for the fold. Raises MemberAbortError on
            # an exhausted member -> orchestrator aborts the task.
            _run_map_milestone(
                dispatcher, writer, pr, leaf_ref, spec, blackboard,
                mm, run_scope or task_run.iri, leaf_idx, run_attempt,
                capacity_graphs,
            )
        elif real_mode and kind == "fold":
            # Slice 1b — dispatch the L3 reducer over the ordered member outputs.
            _run_fold_milestone(
                dispatcher, writer, pr, leaf_ref, spec, blackboard,
            )
        elif real_mode and endpoints is not None:
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


def _run_map_milestone(
    dispatcher, writer, pr, leaf_ref, spec, blackboard,
    mm, task_id: str, leaf_idx: int, run_attempt: int,
    capacity_graphs: Optional[list],
) -> None:
    """Map fan-out (collection-iteration Slice 1b).

    Read the ordered collection value from the shared blackboard (ADR-0199: L4
    owns the unpack loop) and, for each member **sequentially** (v1), run a
    uniform sub-pipeline ``find_pipeline(member_ds -> sub_target)`` in an isolated
    sub-blackboard seeded with just the member value, under a fresh per-member
    run-ref so its ``capacity_mm`` grounding graph stays isolated. Bounded retry:
    accept the first attempt with ``success=True`` (only its grounding graph is
    persisted; rejected attempts leave nothing in ``capacity_graphs``). ∀-abort: a
    member still failing at ``MEMBER_RETRY_CAP`` raises :class:`MemberAbortError`
    — remaining members are skipped and the fold never runs. On success, writes
    the ordered list of members' ``sub_target`` outputs to ``blackboard[out_ds]``
    for the fold."""
    collection_ds = spec["collection_ds"]
    member_ds = spec["member_ds"]
    sub_target = spec["sub_target"]
    out_ds = spec["out_ds"]
    members = list(blackboard.get(collection_ds) or [])
    member_outputs: List[Any] = []
    for member_idx, member_value in enumerate(members):
        accepted = None
        last_pipeline = None
        for retry_idx in range(MEMBER_RETRY_CAP):
            run_ref = (
                f"pipelinerun:{task_id}:{leaf_idx}:m{member_idx}"
                f":{run_attempt}:r{retry_idx}"
            )
            result, last_pipeline = _run_member_pipeline(
                dispatcher, member_ds, member_value, sub_target,
                task_id, run_ref, mm,
            )
            if result.success:
                accepted = result
                break  # accept the first clean attempt
        if accepted is None:
            # ∀-abort: this member exhausted the retry cap still failing.
            pr.status = "failed"
            for step in getattr(last_pipeline, "steps", ()) or ():
                writer.emit_step_execution_record(
                    step.capacity_iri,
                    pipeline_run_ref=pr.iri,
                    milestone_ref=leaf_ref,
                    confidence=0.0,
                )
            raise MemberAbortError(leaf_ref, member_idx)
        # Accepted attempt only: persist its grounding graph + per-step records.
        if capacity_graphs is not None and accepted.capacity_graph is not None:
            capacity_graphs.append(accepted.capacity_graph)
        for step in getattr(last_pipeline, "steps", ()) or ():
            writer.emit_step_execution_record(
                step.capacity_iri,
                pipeline_run_ref=pr.iri,
                milestone_ref=leaf_ref,
                confidence=1.0,
            )
        member_outputs.append(accepted.outputs.get(sub_target))
    blackboard[out_ds] = member_outputs
    pr.status = "completed"


def _run_member_pipeline(
    dispatcher, start_ds, seed_value, target_ds,
    task_id: str, run_ref: str, mm,
):
    """Find + run one member's sub-pipeline, isolated per member (Slice 1b).

    Pure — no writer / ``capacity_graphs`` side effects: the caller
    (:func:`_run_map_milestone`) decides accept/reject, so a rejected retry
    attempt leaves nothing persisted. Seeds only the member value under
    ``start_ds`` into a fresh sub-blackboard (per-member grounding isolated by the
    fresh ``run_ref``). Returns ``(PipelineExecutionResult, pipeline)``."""
    from mindsos_capacity.exceptions import PipelineNotFoundError
    from mindsos_capacity.pipeline import find_pipeline

    from .pipeline_execution import execute_pipeline

    try:
        pipeline = find_pipeline(
            dispatcher.capacity_layer,
            session=dispatcher.session,
            start_datastate=start_ds,
            target_datastate=target_ds,
        )
    except PipelineNotFoundError:
        pipeline = find_pipeline(
            dispatcher.capacity_layer,
            session=None,
            start_datastate=start_ds,
            target_datastate=target_ds,
        )
    seed = (
        {start_ds: seed_value}
        if start_ds in pipeline.start_datastates
        else {}
    )
    result = execute_pipeline(
        dispatcher,
        pipeline,
        seed,
        task_id=task_id,
        mm=mm,
        pipeline_run_ref=run_ref,
    )
    return result, pipeline


def _run_fold_milestone(
    dispatcher, writer, pr, leaf_ref, spec, blackboard,
) -> None:
    """Fold / barrier-aggregate (collection-iteration Slice 1b).

    Reaching the fold means the map's ∀-abort barrier already passed (every
    member succeeded — a failed member would have raised before this milestone).
    Dispatch the plan-named L3 **reducer** capacity over the ordered member
    outputs on the blackboard (``in_ds`` = the map's ``out_ds``) and merge its
    outputs back for downstream stages. This is the real aggregation the unused
    ``planning_v0.aggregate_outputs`` stub only stood in for. A reducer that
    concludes "no consistent rule" produces a legitimate value (→ ``dont_know``
    via the existing ``sufficient_predicate`` path), NOT an abort."""
    reducer_iri = spec["reducer_iri"]
    in_ds = spec["in_ds"]
    result = dispatcher.dispatch(reducer_iri, {in_ds: blackboard.get(in_ds)})
    success = bool(getattr(result, "success", False))
    if success:
        blackboard.update(dict(getattr(result, "outputs", {}) or {}))
    writer.emit_step_execution_record(
        reducer_iri,
        pipeline_run_ref=pr.iri,
        milestone_ref=leaf_ref,
        confidence=1.0 if success else 0.0,
    )
    pr.status = "completed" if success else "failed"


__all__ = ["run", "MemberAbortError", "MEMBER_RETRY_CAP"]
