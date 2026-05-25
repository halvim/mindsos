"""Phase 30 — invoke() exception path emits ProblemTraceRecord (ADR-0072)."""

from __future__ import annotations

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    build_failing_capacity,
    build_min_layer,
)


def test_invoke_captures_exception_into_envelope():
    cl = build_min_layer()
    boom = build_failing_capacity()
    cl.register_capacity(boom)

    result = cl.invoke(
        boom.iri,
        inputs={DS_INPUT_IRI: "anything"},
        task_id="task-1",
        step_id="step-1",
    )

    assert result.success is False
    assert isinstance(result.error, RuntimeError)
    assert "intentional" in str(result.error)
    assert result.outputs == {}


def test_invoke_emits_problem_trace_record_on_exception():
    cl = build_min_layer()
    boom = build_failing_capacity()
    cl.register_capacity(boom)

    cl.invoke(
        boom.iri,
        inputs={DS_INPUT_IRI: "anything"},
        task_id="task-1",
        step_id="step-1",
    )

    records = cl.problem_trace.records()
    assert len(records) == 1
    rec = records[0]
    assert rec.error_kind == "exception:RuntimeError"
    assert rec.task_id == "task-1"
    assert rec.step_id == "step-1"
    assert rec.capacity_iri == boom.iri
    assert "intentional" in rec.payload["message"]


def test_invoke_without_task_id_skips_trace_emission_foot_gun():
    """R1 PB-16 lock — task_id=None silently skips trace emission.

    Envelope still returned with success=False; sink stays empty.
    """
    cl = build_min_layer()
    boom = build_failing_capacity()
    cl.register_capacity(boom)

    result = cl.invoke(boom.iri, inputs={DS_INPUT_IRI: "x"})

    assert result.success is False
    assert isinstance(result.error, RuntimeError)
    assert len(cl.problem_trace) == 0
