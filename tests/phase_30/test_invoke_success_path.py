"""Phase 30 — invoke() success-path envelope."""

from __future__ import annotations

from mindsos_capacity import InvocationResult

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_OUTPUT_IRI,
    build_echo_capacity,
    build_min_layer,
)


def test_invoke_returns_success_envelope():
    cl = build_min_layer()
    echo = build_echo_capacity()
    cl.register_capacity(echo)

    result = cl.invoke(echo.iri, inputs={DS_INPUT_IRI: "hello"})

    assert isinstance(result, InvocationResult)
    assert result.success is True
    assert result.error is None
    assert result.outputs == {DS_OUTPUT_IRI: "hello"}


def test_invoke_records_duration_ms():
    cl = build_min_layer()
    echo = build_echo_capacity()
    cl.register_capacity(echo)
    result = cl.invoke(echo.iri, inputs={DS_INPUT_IRI: "x"})
    assert result.duration_ms >= 0


def test_invoke_trace_dict_records_inputs_outputs_keys():
    cl = build_min_layer()
    echo = build_echo_capacity()
    cl.register_capacity(echo)
    result = cl.invoke(echo.iri, inputs={DS_INPUT_IRI: "x"})
    assert result.trace["capacity"] == echo.iri
    assert DS_INPUT_IRI in result.trace["inputs_keys"]
    assert DS_OUTPUT_IRI in result.trace["outputs_keys"]


def test_invoke_emits_no_problem_trace_on_success():
    cl = build_min_layer()
    echo = build_echo_capacity()
    cl.register_capacity(echo)
    cl.invoke(echo.iri, inputs={DS_INPUT_IRI: "x"}, task_id="t1")
    assert len(cl.problem_trace) == 0
