"""Core pipeline-step executor — run a :class:`~mindsos_capacity.pipeline.Pipeline`
for real (RULES §8: this is a **core** MindsOS component, not a subsystem's).

The Phase-47 ``execution.run`` leaf-runner emits only a *notional* step
record (real capacity bodies were stubbed). This module is the real thing
at the **Pipeline** level: walk a Pipeline's topologically-ordered
``DAGStep`` s, dispatch each capacity through the L4 dispatcher, thread
DataState values step-to-step on a blackboard, and stop on the first
failure. *Plan/Milestone* orchestration (MSUR/SCMS) stays in the
orchestrator — this is one Pipeline, one pass.

First consumer is the SubMind resolver (``submind_arbiter``): a SubMind's
resolver is a *goal*, and the goal is reached by a Pipeline the finder
builds at dispatch time from whatever capabilities the system currently
has. A single capacity is the degenerate 1-step Pipeline, so there is no
"single capacity vs pipeline" special case — everything is a Pipeline.

Dispatcher contract (duck-typed so tests can inject a fake): a
``.dispatch(capacity_iri, inputs, *, cancel_token=None, request_id=None,
step_id=None)`` returning an object with ``.success: bool`` and
``.outputs: Mapping[str, Any]`` (the shipped
:class:`~mindsos_capacity.runtime.InvocationResult`). Output keys are
DataState IRIs and are merged onto the blackboard.

**L5 grounding (CR#4 Slice 2, ADR-0201; per-run graph — CR: capacity_mm
persist Slice A).** When an ``mm`` is supplied, the executor additionally
records each invocation into ``mm.capacity_mm`` as a grounding DAG via
:class:`~mindsos_intelligence.capacity_mm_writer.CapacityMMWriter` (DQ-3
"L5 IS the blackboard"), keyed on ``(request_id, pipeline_run_ref)``. ``mm=None``
(the default) is byte-identical to the pre-Slice-2 behavior — value-only
threading, no MM write — which is the sanctioned path for interpret-resolve
and isolated tests (B2). The value dict is retained for dispatch-input
assembly; the MM holds the durable grounding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

# L-2 run-stopped reason tokens. ``identifiers`` is a leaf module (no upward
# imports), so this is safe at module level — unlike ``capacity_mm_writer``,
# which stays a local import inside the function to keep the graph light.
from mindsos_capacity.identifiers import (
    RUN_STOPPED_EMPTY_DOMAIN,
    RUN_STOPPED_NEEDS_INPUT,
    RUN_STOPPED_PARTIAL_DOMAIN,
    RUN_STOPPED_STEP_FAILED,
)

#: The reasons a caller may order a stop BEFORE the first dispatch (ADR-0201
#: am-5/am-6). Closed on purpose: an unknown token raises rather than minting
#: an untranslatable stop.
_PRE_DISPATCH_STOP_REASONS = frozenset(
    {RUN_STOPPED_EMPTY_DOMAIN, RUN_STOPPED_PARTIAL_DOMAIN}
)


@dataclass(frozen=True)
class PipelineExecutionResult:
    """Outcome of running one Pipeline.

    * ``success`` — every step succeeded (or the Pipeline was a no-op).
    * ``outputs`` — the final blackboard (every DataState value produced
      or supplied), so the caller can read ``target_datastate``.
    * ``failed_step`` — the ``capacity_iri`` of the first failing step,
      else ``None``.
    * ``cancelled`` — execution stopped because the cancel token was set
      before a step (cooperative; mid-pipeline preemption).
    * ``error`` — the underlying ``InvocationResult.error`` of the
      failing step, if any.
    * ``needs_input`` — the ``NeedsInput`` verdict a step's body returned
      (ADR-0196); the walk halts and bubbles it (``success=False``). The
      caller (e.g. ``phase_1.interpret``) surfaces it to the user.
    """

    success: bool
    outputs: Dict[str, Any] = field(default_factory=dict)
    failed_step: Optional[str] = None
    cancelled: bool = False
    error: Optional[BaseException] = None
    steps_run: int = 0
    needs_input: Optional[Any] = None
    #: This run's ``capacity_mm`` grounding graph (the ``CapacityMMWriter``'s
    #: per-run graph), or ``None`` when no ``mm`` was supplied / nothing was
    #: written. Exposed so the solve-path caller (Step 5, ``execution.run``)
    #: can hand the graph to ``consolidate_task`` for Slice-B persistence
    #: without re-reaching into the writer.
    capacity_graph: Optional[Any] = None
    #: ADR-0201 amendment 5 — set to the stop reason token when the caller
    #: ordered a stop BEFORE the first dispatch (``stop_before_dispatch``);
    #: the run grounded (manifest + seeds + ``RunStopped`` alone) but no step
    #: ran. ``None`` on every other path.
    stopped_before_dispatch: Optional[str] = None


def _is_cancelled(token: Any) -> bool:
    if token is None:
        return False
    is_set = getattr(token, "is_set", None)
    return bool(is_set()) if callable(is_set) else False


def execute_pipeline(
    dispatcher: Any,
    pipeline: Any,
    initial_inputs: Optional[Mapping[str, Any]] = None,
    *,
    request_id: str,
    cancel_token: Any = None,
    mm: Any = None,
    pipeline_run_ref: Optional[str] = None,
    case_label: Optional[str] = None,
    member_graph_ids: Optional[Any] = None,
    stop_before_dispatch: Optional[str] = None,
    stop_detail: Optional[str] = None,
) -> PipelineExecutionResult:
    """Execute ``pipeline`` step-by-step via ``dispatcher``.

    ``initial_inputs`` seeds the blackboard with the values of the
    Pipeline's ``start_datastates`` (keyed by DataState IRI). Steps are
    assumed topologically ordered (the finder's contract), so a simple
    forward walk threads producer outputs to downstream consumers.

    The cancel token is polled **between** steps (cooperative): a set
    token stops the walk and returns ``cancelled=True`` — this is how a
    higher-priority need / Reflex preempts a running resolver without a
    forced kill mid-capacity.

    ``mm`` (CR#4 Slice 2, optional): when supplied, each start input and each
    invocation output is recorded into ``mm.capacity_mm`` as a grounding DAG
    (ADR-0201) via :class:`CapacityMMWriter`, under the MM write lock and never
    across a dispatch. ``pipeline_run_ref`` is then **required** and scopes the
    per-run instance graph + minted instance IRIs — it must be a fresh
    per-run reference (a ``pipelinerun:`` IRI). There is **no** default: the old
    ``run_ref = request_id`` fallback silently collided on replan (a second run
    re-minted identical IRIs into the same graph), so ``mm`` present with
    ``pipeline_run_ref=None`` is a ``ValueError`` (CR: capacity_mm persist
    Slice A). ``mm=None`` leaves behavior byte-identical to the pre-Slice-2
    value-only path (``pipeline_run_ref`` is ignored).

    ``case_label`` is written onto the run's manifest node verbatim and is
    **never invented here**. Core has no way to know which of a consumer's cases
    a run is, and a label core made up would print on the page as if the system
    had recognised something. Absent (the default) means the manifest says the
    run carried no label, which a renderer must be able to tell apart from a
    label it failed to read.

    ``member_graph_ids`` (ADR-0201 amendment 5) rides onto the run's manifest
    verbatim — supplied by ``_run_fold_milestone`` only (the ordered member
    grounding-graph ids); ``None`` leaves the manifest key absent.

    ``stop_before_dispatch`` (ADR-0201 amendment 5): when set to a stop
    reason token, the run GROUNDS — manifest, seeded starts — and then stops
    before the first dispatch, minting the terminal ``RunStopped`` node ALONE
    (no CapacityInstance: no capacity ran — guard G3), with ``stop_detail``
    as its prose detail. The caller decides the stop (it is milestone-level
    policy, e.g. an empty fold domain); this function is where it grounds,
    because a hand-mint at the milestone would be a second copy of the drift
    the fold-grounding CR removed. Closed to ``_PRE_DISPATCH_STOP_REASONS``
    (``empty_domain``, am-5; ``partial_domain``, am-6) — an unknown token
    raises rather than minting an untranslatable stop.
    """
    if stop_before_dispatch is not None and stop_before_dispatch not in _PRE_DISPATCH_STOP_REASONS:
        raise ValueError(
            f"stop_before_dispatch supports only {sorted(_PRE_DISPATCH_STOP_REASONS)} "
            f"(ADR-0201 am-5/am-6), got {stop_before_dispatch!r}"
        )
    blackboard: Dict[str, Any] = dict(initial_inputs or {})

    # CR#4 Slice 2 — optional L5 grounding writer (B2: write only when an MM
    # is present; the no-MM path is unchanged). Seed the start inputs as
    # DataStateInstances so downstream CONSUMES edges have a producer to point at.
    writer = None
    if mm is not None:
        if pipeline_run_ref is None:
            raise ValueError(
                "execute_pipeline requires an explicit `pipeline_run_ref` when "
                "`mm` is supplied: the removed `run_ref = request_id` default "
                "collided on replan (a second run under the same task re-minted "
                "identical instance IRIs and overwrote the first run). Pass a "
                "fresh per-run reference (a `pipelinerun:` IRI) — CR: capacity_mm "
                "persist Slice A."
            )
        from .capacity_mm_writer import (
            CapacityMMWriter,
            capacity_phrases,
            start_phrases,
        )

        writer = CapacityMMWriter(mm, request_id, pipeline_run_ref)
        # The manifest is minted HERE, before any other node, and the placement
        # is the change. It used to be minted by
        # ``execution._run_leaf_pipeline``, which is one of TWO run paths: a map
        # member goes through ``_run_member_pipeline`` instead, so every
        # member's grounding graph carried no manifest at all. That was found by
        # running a three-member map — 3 graphs, 3 capacity instances each, 0
        # manifests — not by reading the code. Minting it in the one function
        # BOTH paths call makes "every graph carries a manifest" a property of
        # the executor rather than of whichever caller remembered to.
        #
        # ``declared_starts`` is keyed on what was actually SEEDED, not on
        # ``pipeline.start_datastates``: a seeded value is exactly what becomes
        # a parentless DataStateInstance, and a declared start with no value
        # mints no node, so naming it would promise a renderer a premise that is
        # not in the graph. ``blackboard`` is still the untouched
        # ``initial_inputs`` at this point — the walk has not run.
        writer.manifest(
            declared_starts=start_phrases(dispatcher, tuple(blackboard)),
            capacity_phrases=capacity_phrases(dispatcher, pipeline),
            case_label=case_label,
            member_graph_ids=member_graph_ids,
        )
        for ds, value in blackboard.items():
            # Idempotent seed: a start input already carried in the index (e.g.
            # a raw_task root the caller pre-minted) is not re-minted. Empty
            # index on the submind / interpret paths → every start seeds, so
            # those are byte-identical.
            if ds not in writer.index:
                writer.seed(ds, value)

    def _cap_graph():
        return writer.graph if writer is not None else None

    steps = tuple(getattr(pipeline, "steps", ()) or ())

    if stop_before_dispatch is not None:
        # ADR-0201 amendment 5 — the caller ruled the run must not reach its
        # first dispatch (empty fold domain). The graph above is real
        # (manifest + seeds); the stop node is minted ALONE, before-capacity
        # = the step that would have run.
        if writer is not None:
            recorder = (
                writer.record_partial_domain
                if stop_before_dispatch == RUN_STOPPED_PARTIAL_DOMAIN
                else writer.record_empty_domain
            )
            recorder(
                before_capacity_iri=(
                    steps[0].capacity_iri if steps else None
                ),
                detail=stop_detail,
            )
        return PipelineExecutionResult(
            success=False, outputs=blackboard, steps_run=0,
            capacity_graph=_cap_graph(),
            stopped_before_dispatch=stop_before_dispatch,
        )

    # No-op pipeline: the target is already available (target ∈ starts).
    if not steps:
        return PipelineExecutionResult(
            success=True, outputs=blackboard, steps_run=0,
            capacity_graph=_cap_graph(),
        )

    for idx, step in enumerate(steps):
        if _is_cancelled(cancel_token):
            # L-2 — a terminal node on every non-success, so a stopped run is
            # renderable from the grounding graph. Cancellation is the case
            # where the step never dispatched, so it mints the RunStopped node
            # ALONE: no CapacityInstance, because no capacity ran.
            if writer is not None:
                writer.record_cancelled(before_capacity_iri=step.capacity_iri)
            return PipelineExecutionResult(
                success=False, outputs=blackboard, cancelled=True, steps_run=idx,
                capacity_graph=_cap_graph(),
            )
        inputs = {
            ds: blackboard[ds]
            for ds in step.input_datastates
            if ds in blackboard
        }
        result = dispatcher.dispatch(
            step.capacity_iri,
            inputs,
            cancel_token=cancel_token,
            request_id=request_id,
            step_id=f"{request_id}-step-{idx}",
        )
        # ADR-0196 — a step asked the user; halt the walk and bubble the
        # verdict (before the success check: needs_input carries success=True
        # with empty outputs, but is not a completed step).
        step_needs_input = getattr(result, "needs_input", None)
        if step_needs_input is not None:
            # L-2 — the body RAN and deliberately asked, so the invocation is
            # real: CapacityInstance + CONSUMES, then the terminal node.
            if writer is not None:
                writer.record_stopped(
                    step.capacity_iri,
                    step.input_datastates,
                    RUN_STOPPED_NEEDS_INPUT,
                    detail=getattr(step_needs_input, "missing", None),
                )
            return PipelineExecutionResult(
                success=False,
                outputs=blackboard,
                needs_input=step_needs_input,
                steps_run=idx,
                capacity_graph=_cap_graph(),
            )
        if not getattr(result, "success", False):
            # L-2 — the body ran and raised. Same shape as needs_input: the
            # invocation happened, so it is in the graph, and the CONSUMES
            # edges hang the failure off the values that led to it.
            step_error = getattr(result, "error", None)
            if writer is not None:
                writer.record_stopped(
                    step.capacity_iri,
                    step.input_datastates,
                    RUN_STOPPED_STEP_FAILED,
                    detail=str(step_error) if step_error is not None else None,
                    # The two channels, kept apart: the detail is the prose a
                    # Record prints, and this is the closed token code reads.
                    # Only an OUR-FAULT exception carries one (an outage, a
                    # ceiling); a body failing on the customer's data carries
                    # none, and its absence is the answer to "was this ours".
                    fault_reason=getattr(step_error, "refusal_reason", None),
                )
            return PipelineExecutionResult(
                success=False,
                outputs=blackboard,
                failed_step=step.capacity_iri,
                error=step_error,
                steps_run=idx,
                capacity_graph=_cap_graph(),
            )
        outs = dict(getattr(result, "outputs", {}) or {})
        # CR#4 Slice 2 — ground the completed invocation into capacity_mm
        # (between dispatches; the writer takes/releases the MM lock itself,
        # so it is never held across the dispatch above).
        if writer is not None:
            writer.record(step.capacity_iri, step.input_datastates, outs)
        for ds, value in outs.items():
            blackboard[ds] = value

    return PipelineExecutionResult(
        success=True, outputs=blackboard, steps_run=len(steps),
        capacity_graph=_cap_graph(),
    )


__all__ = ["PipelineExecutionResult", "execute_pipeline"]
