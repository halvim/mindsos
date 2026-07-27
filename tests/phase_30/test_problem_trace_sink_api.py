"""Phase 30 — ProblemTraceSink API (records / drain / __len__; ADR-0074)."""

from __future__ import annotations

from mindsos_capacity import (
    ProblemTraceRecord,
    ProblemTraceSink,
    emit_problem_trace,
)


def test_empty_sink_starts_empty():
    sink = ProblemTraceSink()
    assert len(sink) == 0
    assert sink.records() == []


def test_emit_appends_record_to_buffer():
    sink = ProblemTraceSink()
    rec = ProblemTraceRecord(request_id="t1", error_kind="exception:RuntimeError")
    sink.emit(rec)
    assert len(sink) == 1
    assert sink.records() == [rec]


def test_records_returns_a_snapshot_copy():
    sink = ProblemTraceSink()
    rec = ProblemTraceRecord(request_id="t1", error_kind="x")
    sink.emit(rec)
    snapshot = sink.records()
    snapshot.append("not-a-record")  # mutating the snapshot must not affect sink
    assert len(sink) == 1


def test_drain_returns_and_clears_buffer():
    sink = ProblemTraceSink()
    emit_problem_trace(sink, request_id="t1", error_kind="x")
    emit_problem_trace(sink, request_id="t2", error_kind="y")
    assert len(sink) == 2

    drained = sink.drain()
    assert len(drained) == 2
    assert len(sink) == 0
    assert sink.records() == []
