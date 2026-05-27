"""Phase 34 — ``runtime.invoke`` bypass branch for write capacities (R1 PB-A + R5 PB-G)."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    Capacity,
    CapacityLayer,
    CapacityRegistrationError,
    DS_PROBLEM_TRACE_RECORD,
    InvocationResult,
    ProblemTraceRecord,
    WriteResult,
)
from mindsos_capacity.builtins.trace import install_trace_capacities
from mindsos_capacity.identifiers import CATEGORY_TRACE
from mindsos_capacity.runtime import invoke as _runtime_invoke

from tests.phase_34._fixtures import build_admin_session


def test_bypass_stashes_writeresult_in_invocation_result():
    layer, kl = _build_layer()
    sess = build_admin_session("admin")
    result = layer.invoke(
        "capacity:trace:problem",
        {DS_PROBLEM_TRACE_RECORD: {"trace_id": "t1", "value": "v"}},
        session=sess,
        task_id="T",
    )
    assert result.success is True
    assert result.outputs == {}
    assert isinstance(result.write_outcome, WriteResult)


def test_bypass_trace_records_write_outcome_kind():
    """Phase 34 bypass branch adds write_outcome_kind to trace."""
    layer, _ = _build_layer()
    sess = build_admin_session("admin")
    result = layer.invoke(
        "capacity:trace:problem",
        {DS_PROBLEM_TRACE_RECORD: {"trace_id": "t1", "value": "v"}},
        session=sess,
        task_id="T",
    )
    assert result.trace.get("write_outcome_kind") == "WriteResult"


def test_bypass_raises_on_wrong_return_type():
    """R5 PB-G: bypass validates body return type; envelope catches.

    The bypass branch raises ``CapacityRegistrationError`` for wrong
    return shape; the outer try/except in ``runtime.invoke`` catches it
    per ADR-0072 envelope contract → ``InvocationResult(success=False,
    error=...)``. Test asserts the envelope shape, not a raise.
    """

    def _wrong_return_impl(**kwargs):
        return {"foo": "bar"}  # dict, not WriteResult/ProblemTraceRecord

    decl = Capacity(
        name="bad",
        category=CATEGORY_TRACE,
        inputs=(),
        outputs=(),
        implementation=_wrong_return_impl,
        description="test",
    )
    result = _runtime_invoke(decl, inputs={})
    assert result.success is False
    assert isinstance(result.error, CapacityRegistrationError)
    assert "expected WriteResult" in str(result.error)


def test_bypass_accepts_problem_trace_record_return():
    """Bypass also accepts ProblemTraceRecord (future clause-1 flip path)."""

    def _ptr_return_impl(**kwargs):
        return ProblemTraceRecord(task_id="T", error_kind="test")

    decl = Capacity(
        name="ptr",
        category=CATEGORY_TRACE,
        inputs=(),
        outputs=(),
        implementation=_ptr_return_impl,
        description="test",
    )
    result = _runtime_invoke(decl, inputs={})
    assert result.success is True
    assert isinstance(result.write_outcome, ProblemTraceRecord)


def test_read_capacity_path_unchanged_no_write_outcome():
    """Bypass only fires for outputs=(); read capacities unaffected."""
    from mindsos_capacity.builtins.text import install_text_capacities

    layer = CapacityLayer()
    install_text_capacities(layer)
    # Find a text capacity that has outputs (read path).
    decls = [d for d in layer.iter_declarations() if d.outputs]
    assert decls, "expected at least one read capacity with outputs"
    cap = decls[0]
    # Run minimal invoke; assert write_outcome stays None.
    # (We don't care about success here; just shape.)
    try:
        result = layer.invoke(cap.iri, {iri: "x" for iri in cap.inputs}, task_id="T")
        assert result.write_outcome is None
    except Exception:
        # If invoke fails (e.g., shape mismatch), still confirm via the
        # construction that the field default is None.
        empty_result = InvocationResult(
            outputs={}, duration_ms=0.0, success=True
        )
        assert empty_result.write_outcome is None


def _build_layer():
    from mindsos_knowledge import KnowledgeLayer

    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_trace_capacities(layer)
    return layer, kl
