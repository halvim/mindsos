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

**Nesting (collection-iteration Slice 2).**

A map's per-member work may itself be a whole sub-plan rather than a single
``find_pipeline`` leaf — and that sub-plan may itself contain a map/fold (e.g.
objects within grids within a task). A map spec carries this via an optional
``sub_plan`` key (a mini plan: ``{leaf_milestone_refs, pipeline_refs,
milestone_specs, leaf_targets?, solve_target?}``); when present, each member runs
that sub-plan in its own isolated sub-blackboard (seeded with the member value)
instead of the flat 1b leaf, and the map collects ``sub_target`` from that
sub-blackboard. When absent, the member runs the flat 1b path — byte-identical.

The milestone loop is factored into :func:`_run_milestone_sequence`, which both
``run`` (top level) and a map member (its sub-plan) invoke. Every executed leaf's
per-run ref is a **path** — ``pipelinerun:{scope}:{ref_path}[...]`` — that
accumulates a ``{milestone_idx}`` segment per level and an ``m{member_idx}``
segment per map fan-out, so a nested run's grounding graph stays isolated from
its siblings and the provenance tree (the set of per-run graphs, keyed by role)
is walkable by path. At depth 0 the path is just ``{leaf_idx}`` → the refs are
byte-identical to Slice 1a/1b. (Cross-stage grounding *continuity* — linking a
consumer's seeded start to the producer's instance across per-run graphs — is
NOT resolved here: it would reverse the Slice-A per-run-graph / intra-graph-edge
model and is deferred to its own slice. The ref-path gives isolation + a
locatable tree, not connected cross-stage edges.)

Bounded retry + ∀-abort apply at map-member granularity at **every** level: a
nested map enforces its own retry cap and barrier over its members, and a nested
``MemberAbortError`` propagates out unretried (a deterministic load failure that
exhausted its own budget aborts the whole task). A sub-plan member itself is not
retried (retry lives at the flat find+execute leaf where transient load failure
actually occurs); a plain sub-plan stage fails soft exactly as a top-level plain
stage does (1a behaviour, unchanged).

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
    retried at the whole-task level).

    ``member_index`` names the failing member at its own level; with Slice 2
    nesting the abort raised by a nested map propagates unretried through the
    parent members, so the exception that escapes ``run`` names the innermost
    failing member (the deterministic load failure that started the abort)."""

    def __init__(self, leaf_ref: str, member_index: int, message: str = ""):
        self.leaf_ref = leaf_ref
        self.member_index = member_index
        super().__init__(
            message
            or f"map {leaf_ref!r}: member {member_index} failed after "
            f"{MEMBER_RETRY_CAP} attempt(s) (all-or-nothing abort)"
        )


def _parse_member_target(target_ref):
    """Parse a bare top-level map-member ref-path ``"{leaf_idx}:m{member_idx}"``
    into ``(leaf_idx, member_idx)``; ``None`` for anything else.

    Slice 3b targets **only** the unambiguous top-level structural form (exactly
    two segments — a leaf index and an ``m<member>`` segment). A full
    ``pipelinerun:{scope}:…`` grounding ref (the Slice-3 *advisory* address, whose
    scope segment may itself contain ``:``) or a deeper **nested** path
    (``"{i}:m{j}:{k}:m{l}"``, whose members emit interleaved PipelineRuns so the
    flat-list index alignment does not hold) both return ``None`` → the caller
    falls back to a safe whole-pipeline replan (byte-identical to Slice 3)."""
    if not isinstance(target_ref, str) or not target_ref:
        return None
    parts = target_ref.split(":")
    if len(parts) != 2:
        return None
    head, mem = parts
    if not head.isdigit() or not (mem.startswith("m") and mem[1:].isdigit()):
        return None
    return int(head), int(mem[1:])


def resolve_member_target(plan_result, target_ref):
    """Resolve a replan verdict's advisory ``target_ref`` to a re-runnable
    ``(map_leaf_idx, member_idx)`` — Slice 3b, top-level flat map only.

    Returns ``None`` (→ whole-pipeline replan, byte-identical to Slice 3) unless
    ``target_ref`` is a bare ``"{idx}:m{j}"`` path (see :func:`_parse_member_target`)
    AND the named milestone is a ``map`` carrying no ``sub_plan``. Nested targeting
    is deferred with the B/continuity slice: a nested map's members append
    interleaved PipelineRuns, so ``invalidate_at_and_below``'s position-based clear
    would not isolate them."""
    parsed = _parse_member_target(target_ref)
    if parsed is None:
        return None
    map_idx, member_idx = parsed
    leaf_refs = getattr(plan_result, "leaf_milestone_refs", None) or []
    if not (0 <= map_idx < len(leaf_refs)):
        return None
    specs = getattr(plan_result, "milestone_specs", None) or {}
    spec = specs.get(leaf_refs[map_idx])
    if not spec or spec.get("kind") != "map" or spec.get("sub_plan"):
        return None
    return map_idx, member_idx


def run(
    dispatcher,
    writer,
    plan_result,
    request_run,
    *,
    mm: Any = None,
    run_scope: Optional[str] = None,
    solve_seed: Optional[dict] = None,
    capacity_graphs: Optional[list] = None,
    run_attempt: int = 0,
    blackboard: Optional[dict] = None,
    targeted: Optional[tuple] = None,
) -> List[str]:
    """Run each leaf Pipeline; return the top-level PipelineRun IRIs.

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
    it into an aborted task).

    The per-leaf work is delegated to :func:`_run_milestone_sequence` (Slice 2),
    entered here with an empty ``ref_path`` so a top-level leaf's per-run ref is
    ``{leaf_idx}`` — byte-identical to Slice 1a/1b."""
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
    # Slice 1a — one attempt-scoped blackboard threaded across milestones, seeded
    # from ``solve_seed``. Slice 3b — the orchestrator may instead pass a
    # ``blackboard`` retained from the prior attempt so a *targeted* replan reuses
    # the completed siblings' values; ``targeted`` = ``(map_leaf_idx, member_idx)``
    # then resumes the sequence AT that top-level map and re-runs only that one
    # member (splicing it into the retained member outputs), followed by the fold
    # + any downstream. With ``blackboard=None``/``targeted=None`` (every
    # v0/1a/1b/2/3 path) a fresh blackboard is seeded and the whole sequence runs
    # from index 0 — byte-identical.
    bb: dict = blackboard if blackboard is not None else dict(solve_seed or {})
    start_idx, target_member = targeted if targeted is not None else (0, None)
    return _run_milestone_sequence(
        dispatcher, writer, request_run,
        leaf_refs=plan_result.leaf_milestone_refs,
        pipeline_refs=plan_result.pipeline_refs,
        milestone_specs=milestone_specs,
        leaf_targets=leaf_targets,
        solve_target=solve_target,
        blackboard=bb,
        mm=mm,
        scope=run_scope or request_run.iri,
        ref_path="",
        run_attempt=run_attempt,
        capacity_graphs=capacity_graphs,
        real_mode=real_mode,
        start_idx=start_idx,
        target_member=target_member,
    )


def _run_milestone_sequence(
    dispatcher, writer, request_run, *,
    leaf_refs, pipeline_refs, milestone_specs, leaf_targets, solve_target,
    blackboard, mm, scope: str, ref_path: str, run_attempt: int,
    capacity_graphs: Optional[list], real_mode: bool,
    start_idx: int = 0, target_member: Optional[int] = None,
) -> List[str]:
    """Run one ordered sequence of milestones over a shared ``blackboard`` and
    return the emitted PipelineRun IRIs (collection-iteration Slice 2 factoring).

    Shared by ``run`` (top level, ``ref_path=""``) and each map member's sub-plan
    (``ref_path`` = the member's path). Each milestone's per-run ref path is
    ``{ref_path}:{leaf_idx}`` (or ``{leaf_idx}`` at the top), so grounding graphs
    stay isolated per position and the provenance tree is walkable. The
    ``leaf_targets``/``solve_target``/``milestone_specs`` are read exactly as the
    top-level loop did; ``real_mode`` gates the real-vs-notional branch (a nested
    sub-plan is inherently real — ``mm`` is present). Every emitted PipelineRun is
    appended to ``request_run.pipeline_runs`` (a flat list; the tree lives in the
    ref-path — Slice 2 decision)."""
    pipeline_run_refs: List[str] = []
    for leaf_idx, leaf_ref in enumerate(leaf_refs):
        # Slice 3b — on a targeted re-execution the prefix milestones (before the
        # named map at ``start_idx``) already ran in the prior attempt and their
        # values are retained on the reused blackboard; skip them (no re-emit, no
        # re-run). With ``start_idx=0`` (every non-targeted call) nothing is
        # skipped — byte-identical.
        if leaf_idx < start_idx:
            continue
        pipeline_ref = pipeline_refs.get(leaf_ref)
        pr = writer.emit_pipeline_run(pipeline_ref, leaf_ref, request_run.iri)
        spec = milestone_specs.get(leaf_ref)
        kind = spec.get("kind") if spec else None
        leaf_path = f"{ref_path}:{leaf_idx}" if ref_path else f"{leaf_idx}"
        endpoints = leaf_targets.get(leaf_ref) or solve_target
        if real_mode and kind == "map":
            # Slice 1b/2 — fan out a uniform sub-plan over the collection's
            # members (∀-abort barrier + bounded retry inside); a member's work
            # is either the flat 1b leaf or a nested sub-plan (Slice 2). Writes
            # the ordered member outputs to the blackboard for the fold. Raises
            # MemberAbortError on an exhausted member -> orchestrator aborts.
            # Slice 3b — when this is the targeted map (``leaf_idx == start_idx``
            # and a member was named) re-run only that one member; else the full
            # fan-out (``only_member=None`` → byte-identical).
            only_member = (
                target_member
                if (target_member is not None and leaf_idx == start_idx)
                else None
            )
            _run_map_milestone(
                dispatcher, writer, request_run, pr, leaf_ref, spec, blackboard,
                mm, scope, leaf_path, run_attempt, capacity_graphs,
                only_member=only_member,
            )
        elif real_mode and kind == "fold":
            # Slice 1b — dispatch the L3 reducer over the ordered member outputs.
            _run_fold_milestone(
                dispatcher, writer, pr, leaf_ref, spec, blackboard,
            )
        elif real_mode and endpoints is not None:
            outputs = _run_leaf_pipeline(
                dispatcher, writer, pr, leaf_ref, endpoints, blackboard,
                mm, scope, leaf_path, run_attempt, capacity_graphs,
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
        request_run.pipeline_runs.append(pr.iri)
    return pipeline_run_refs


def _run_leaf_pipeline(
    dispatcher, writer, pr, leaf_ref, endpoints, blackboard,
    mm, request_id: str, leaf_path: str, run_attempt: int,
    capacity_graphs: Optional[list],
) -> dict:
    """Find + run the real leaf pipeline; ground it into ``capacity_mm``, collect
    its per-run graph, and return its outputs (for the caller to thread onto the
    run blackboard). Local imports keep this module's import graph light and
    cycle-free (``pipeline_execution`` reaches ``capacity_mm_writer`` → ``mm`` →
    core, none of which import ``execution``). ``leaf_path`` (Slice 2) is the
    milestone's ref-path position; at depth 0 it is ``str(leaf_idx)`` so the ref
    is byte-identical to Slice 1a/1b."""
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
    run_ref = f"pipelinerun:{request_id}:{leaf_path}:{run_attempt}"
    result = execute_pipeline(
        dispatcher,
        pipeline,
        seed,
        request_id=request_id,
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
    dispatcher, writer, request_run, pr, leaf_ref, spec, blackboard,
    mm, request_id: str, leaf_path: str, run_attempt: int,
    capacity_graphs: Optional[list],
    only_member: Optional[int] = None,
) -> None:
    """Map fan-out (collection-iteration Slice 1b; nesting Slice 2).

    Read the ordered collection value from the shared blackboard (ADR-0199: L4
    owns the unpack loop) and, for each member **sequentially** (v1), produce its
    ``sub_target`` output. A member's work is one of:

    * **Flat leaf (1b)** — ``find_pipeline(member_ds -> sub_target)`` +
      ``execute_pipeline`` in an isolated sub-blackboard seeded with just the
      member value, under a fresh per-member run-ref so its ``capacity_mm``
      grounding graph stays isolated. Bounded retry: accept the first attempt
      with ``success=True`` (only its grounding graph is persisted; rejected
      attempts leave nothing in ``capacity_graphs``). ∀-abort: a member still
      failing at ``MEMBER_RETRY_CAP`` raises :class:`MemberAbortError`.
    * **Sub-plan (Slice 2)** — when ``spec["sub_plan"]`` is present, the member
      runs that nested milestone sequence in its own isolated sub-blackboard
      (seeded with the member value) under the member's ref-path, and the map
      collects ``sub_target`` from that sub-blackboard. The sub-plan may itself
      contain a nested map/fold; a nested ``MemberAbortError`` propagates
      unretried (all-or-nothing at every level). The sub-plan member itself is
      not retried — retry lives at the flat find+execute leaf inside it.

    On success, writes the ordered list of members' ``sub_target`` outputs to
    ``blackboard[out_ds]`` for the fold. Remaining members are skipped once any
    member aborts (the fold never runs)."""
    collection_ds = spec["collection_ds"]
    out_ds = spec["out_ds"]
    members = list(blackboard.get(collection_ds) or [])
    if only_member is not None:
        # Slice 3b — targeted: re-run just this one member and splice its output
        # into the retained ordered outputs; the untargeted siblings (and their
        # grounding graphs) are left untouched. The orchestrator bumps
        # ``run_attempt`` for the re-run, so its grounding ref is fresh and never
        # overwrites the prior attempt's (Slice-A isolation).
        existing = list(blackboard.get(out_ds) or [])
        output = _run_one_member(
            dispatcher, writer, request_run, pr, leaf_ref, spec, mm,
            request_id, leaf_path, only_member, members[only_member],
            run_attempt, capacity_graphs,
        )
        if only_member < len(existing):
            existing[only_member] = output
        else:
            existing.append(output)
        blackboard[out_ds] = existing
        pr.status = "completed"
        return
    member_outputs: List[Any] = []
    for member_idx, member_value in enumerate(members):
        member_outputs.append(
            _run_one_member(
                dispatcher, writer, request_run, pr, leaf_ref, spec, mm,
                request_id, leaf_path, member_idx, member_value,
                run_attempt, capacity_graphs,
            )
        )
    blackboard[out_ds] = member_outputs
    pr.status = "completed"


def _run_one_member(
    dispatcher, writer, request_run, pr, leaf_ref, spec, mm,
    request_id: str, leaf_path: str, member_idx: int, member_value: Any,
    run_attempt: int, capacity_graphs: Optional[list],
) -> Any:
    """Run one map member and return its ``sub_target`` output (Slice 3b factoring).

    Extracted from the map loop so the full fan-out and a targeted single-member
    re-run (:func:`_run_map_milestone`) share one code path. A member's work is a
    nested sub-plan (Slice 2) or the flat 1b ``find_pipeline`` + ``execute_pipeline``
    leaf with bounded retry + accept-first-clean; an exhausted member raises
    :class:`MemberAbortError` (∀-abort). Behaviour is unchanged from the inline
    Slice-1b/2 loop."""
    member_ds = spec["member_ds"]
    sub_target = spec["sub_target"]
    sub_plan = spec.get("sub_plan")  # Slice 2 — nested plan (optional)
    member_path = f"{leaf_path}:m{member_idx}"
    if sub_plan is not None:
        # Slice 2 — the member's work is a whole sub-plan (which may nest a
        # further map/fold). Run it once in an isolated sub-blackboard seeded with
        # the member value; a nested ∀-abort raises and propagates unretried.
        sub_blackboard: dict = {member_ds: member_value}
        _run_milestone_sequence(
            dispatcher, writer, request_run,
            leaf_refs=sub_plan["leaf_milestone_refs"],
            pipeline_refs=sub_plan.get("pipeline_refs") or {},
            milestone_specs=sub_plan.get("milestone_specs") or {},
            leaf_targets=sub_plan.get("leaf_targets") or {},
            solve_target=sub_plan.get("solve_target"),
            blackboard=sub_blackboard,
            mm=mm,
            scope=request_id,
            ref_path=member_path,
            run_attempt=run_attempt,
            capacity_graphs=capacity_graphs,
            real_mode=True,
        )
        return sub_blackboard.get(sub_target)
    # Flat 1b member (no sub_plan): bounded retry + accept-first-clean.
    accepted = None
    last_pipeline = None
    for retry_idx in range(MEMBER_RETRY_CAP):
        run_ref = (
            f"pipelinerun:{request_id}:{member_path}"
            f":{run_attempt}:r{retry_idx}"
        )
        result, last_pipeline = _run_member_pipeline(
            dispatcher, member_ds, member_value, sub_target,
            request_id, run_ref, mm,
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
    return accepted.outputs.get(sub_target)


def _run_member_pipeline(
    dispatcher, start_ds, seed_value, target_ds,
    request_id: str, run_ref: str, mm,
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
        request_id=request_id,
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


__all__ = ["run", "MemberAbortError", "MEMBER_RETRY_CAP", "resolve_member_target"]
