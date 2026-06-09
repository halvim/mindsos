"""Phase 34 — CapacityLayer kl= constructor + context["kl"] injection."""

from __future__ import annotations

from mindsos_capacity import CapacityLayer, DS_PROBLEM_TRACE_RECORD
from mindsos_capacity.builtins.trace import install_trace_capacities
from mindsos_knowledge import KnowledgeLayer

from tests.phase_34._fixtures import build_admin_session


def test_capacitylayer_accepts_kl_kwarg():
    """R0 PB-5: __init__ gains optional kl=."""
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    assert layer._kl is kl


def test_capacitylayer_default_kl_is_none():
    """Legacy Phase 28+ construction stays valid."""
    layer = CapacityLayer()
    assert layer._kl is None


def test_invoke_injects_kl_into_context_when_kl_present():
    """R5 PB-B: conditional injection — only when self._kl is not None."""
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_trace_capacities(layer)
    sess = build_admin_session("admin")
    # Invoke a write capacity; it will fail with RuntimeError if KL was
    # NOT injected. Success here proves injection fired.
    result = layer.invoke(
        "capacity:trace:problem",
        {DS_PROBLEM_TRACE_RECORD: {"trace_id": "t1", "value": "ok"}},
        session=sess,
        task_id="T",
    )
    assert result.success is True


def test_invoke_without_kl_yields_runtime_error_via_envelope():
    """R3 PB-F: missing-KL is programmer error; surfaces via envelope."""
    layer = CapacityLayer()  # no kl
    install_trace_capacities(layer)
    sess = build_admin_session("admin")
    result = layer.invoke(
        "capacity:trace:problem",
        {DS_PROBLEM_TRACE_RECORD: {"trace_id": "t1", "value": "ok"}},
        session=sess,
        task_id="T",
    )
    assert result.success is False
    assert isinstance(result.error, RuntimeError)
    # ADR-0180 (Phase 48): with no KL bound, capacity_layer.invoke builds a
    # CapacityContext whose ``writeable`` capability is None; the body raises
    # requiring the pre-authorized write capability (different from the
    # session error).
    assert "writeable" in str(result.error)
    assert "ADR-0180" in str(result.error)
