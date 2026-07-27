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
    """
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
        from .capacity_mm_writer import CapacityMMWriter

        writer = CapacityMMWriter(mm, request_id, pipeline_run_ref)
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

    # No-op pipeline: the target is already available (target ∈ starts).
    if not steps:
        return PipelineExecutionResult(
            success=True, outputs=blackboard, steps_run=0,
            capacity_graph=_cap_graph(),
        )

    for idx, step in enumerate(steps):
        if _is_cancelled(cancel_token):
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
            return PipelineExecutionResult(
                success=False,
                outputs=blackboard,
                needs_input=step_needs_input,
                steps_run=idx,
                capacity_graph=_cap_graph(),
            )
        if not getattr(result, "success", False):
            return PipelineExecutionResult(
                success=False,
                outputs=blackboard,
                failed_step=step.capacity_iri,
                error=getattr(result, "error", None),
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
