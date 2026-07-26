"""Phase 30 — ProblemTraceRecord field shape (R3 PB-17(a) mm_ref kept)."""

from __future__ import annotations

import time

from mindsos_capacity import ProblemTraceRecord


def test_minimal_record_construction():
    rec = ProblemTraceRecord(request_id="t1", error_kind="exception:RuntimeError")
    assert rec.request_id == "t1"
    assert rec.error_kind == "exception:RuntimeError"
    assert rec.step_id is None
    assert rec.mm_ref is None
    assert rec.capacity_iri is None
    assert rec.payload == {}
    assert rec.entry_id  # uuid4 default
    assert rec.timestamp > 0


def test_full_record_construction():
    rec = ProblemTraceRecord(
        request_id="t1",
        error_kind="latency",
        step_id="s1",
        mm_ref="mm:request-42",
        capacity_iri="capacity:perception:test.echo",
        payload={"latency_ms": 1500},
    )
    assert rec.step_id == "s1"
    assert rec.mm_ref == "mm:request-42"
    assert rec.capacity_iri == "capacity:perception:test.echo"
    assert rec.payload == {"latency_ms": 1500}


def test_mm_ref_field_present_but_optional_phase_30_forward_compat():
    """R3 PB-17(a) lock — mm_ref kept as Optional[str] forward-compat for L5.

    PHASE_MAP §0 has L5 out of scope; the field is reserved but unused
    at Phase 30.
    """
    rec = ProblemTraceRecord(request_id="t1", error_kind="x")
    assert rec.mm_ref is None
    # Field exists on the dataclass.
    assert "mm_ref" in rec.__dataclass_fields__


def test_timestamps_increase_monotonically():
    r1 = ProblemTraceRecord(request_id="t1", error_kind="x")
    time.sleep(0.001)
    r2 = ProblemTraceRecord(request_id="t2", error_kind="x")
    assert r2.timestamp >= r1.timestamp


def test_entry_ids_are_unique():
    r1 = ProblemTraceRecord(request_id="t1", error_kind="x")
    r2 = ProblemTraceRecord(request_id="t1", error_kind="x")
    assert r1.entry_id != r2.entry_id
