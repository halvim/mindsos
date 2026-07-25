"""Phase 30 — emit_problem_trace validation (ProblemTraceError raisers)."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    ProblemTraceError,
    ProblemTraceSink,
    emit_problem_trace,
)


def test_emit_returns_constructed_record():
    sink = ProblemTraceSink()
    rec = emit_problem_trace(sink, request_id="t1", error_kind="exception:RuntimeError")
    assert rec.request_id == "t1"
    assert rec.error_kind == "exception:RuntimeError"
    assert len(sink) == 1
    assert sink.records()[0] is rec


def test_empty_task_id_raises():
    sink = ProblemTraceSink()
    with pytest.raises(ProblemTraceError) as exc_info:
        emit_problem_trace(sink, request_id="", error_kind="x")
    assert "task_id" in str(exc_info.value)
    assert len(sink) == 0


def test_empty_error_kind_raises():
    sink = ProblemTraceSink()
    with pytest.raises(ProblemTraceError) as exc_info:
        emit_problem_trace(sink, request_id="t1", error_kind="")
    assert "error_kind" in str(exc_info.value)
    assert len(sink) == 0


def test_payload_dict_copied_not_aliased():
    """Caller-provided payload dict must not be aliased to the record."""
    sink = ProblemTraceSink()
    payload = {"k": "v"}
    rec = emit_problem_trace(sink, request_id="t1", error_kind="x", payload=payload)
    payload["k"] = "MUTATED"
    assert rec.payload == {"k": "v"}
