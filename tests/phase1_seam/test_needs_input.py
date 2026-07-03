"""S2 — ADR-0196 ``needs_input`` verdict.

Covers: the invoke-level envelope, the ``pipeline_execution`` halt+bubble,
``interpret`` returning ``NeedsInput``, and the ``run_lifecycle`` non-terminal
``pending_confirmation`` short-circuit.
"""

from __future__ import annotations

from types import SimpleNamespace

from mindsos_capacity import Capacity, CapacityLayer, DataState, ShapeDescriptor
from mindsos_capacity.identifiers import CATEGORY_DECISION, capacity_iri, datastate_iri
from mindsos_capacity.needs_input import NeedsInput
from mindsos_capacity.runtime import invoke

from mindsos_intelligence import interpret
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.orchestrator import Orchestrator
from mindsos_intelligence.pipeline_execution import (
    PipelineExecutionResult,
    execute_pipeline,
)

from ._fixtures import ARC_CANON_DS, build_consumer, cold_start_resolve, dispatcher_for


# ── invoke-level envelope ────────────────────────────────────────────────


def test_invoke_envelopes_needs_input() -> None:
    """A body returning NeedsInput → InvocationResult.needs_input set,
    outputs empty, success True (it ran fine, it just asked)."""
    ds_in = datastate_iri("t.q_in")
    ds_out = datastate_iri("t.q_out")
    cap = Capacity(
        name="asker",
        category=CATEGORY_DECISION,
        inputs=(ds_in,),
        outputs=(ds_out,),
        implementation=lambda **kw: NeedsInput(question="?", missing=ds_out),
    )
    res = invoke(cap, {ds_in: 1})
    assert isinstance(res.needs_input, NeedsInput)
    assert res.needs_input.question == "?"
    assert res.outputs == {}
    assert res.success is True


# ── pipeline_execution halt+bubble ───────────────────────────────────────


def test_execute_pipeline_bubbles_needs_input() -> None:
    ni = NeedsInput(question="?", missing="ds:x")

    class _Disp:
        def dispatch(self, cap_iri, inputs, **kw):
            return SimpleNamespace(success=True, outputs={}, needs_input=ni)

    pipeline = SimpleNamespace(
        steps=(SimpleNamespace(capacity_iri="c:1", input_datastates=(), output_datastates=()),)
    )
    r = execute_pipeline(_Disp(), pipeline, {}, task_id="t")
    assert isinstance(r, PipelineExecutionResult)
    assert r.needs_input is ni
    assert r.success is False
    assert r.steps_run == 0


# ── interpret returns NeedsInput ─────────────────────────────────────────


def test_interpret_returns_needs_input_on_cold_start() -> None:
    cl, kl, profile = build_consumer(resolve_impl=cold_start_resolve())
    r = interpret(dispatcher_for(cl, kl, profile), "solve task 8")
    assert isinstance(r, NeedsInput)
    assert r.missing == ARC_CANON_DS
    assert r.choices == {"yes": {"text": "solve task id8"}}


# ── run_lifecycle → non-terminal pending_confirmation ────────────────────


def test_run_lifecycle_pending_confirmation() -> None:
    cl, kl, profile = build_consumer(resolve_impl=cold_start_resolve())
    dispatcher = dispatcher_for(cl, kl, profile)
    mm = MentalModel(session_id="s", user_id="u")
    orch = Orchestrator(dispatcher, mm, task_scope="task-1")

    outcome = orch.run_lifecycle("solve task 8")

    assert outcome.status == "pending_confirmation"
    assert isinstance(outcome.pending_confirmation, NeedsInput)
    assert outcome.task_run_ref is None  # no TaskRun on the pending path
    # No consolidation / TaskRun emitted (terminal invariants untouched).
    from mindsos_intelligence.chain_artifacts import TYPE_TASK_RUN, iter_chain_artifacts

    assert not any(True for _ in iter_chain_artifacts(mm, TYPE_TASK_RUN))
