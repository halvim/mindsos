"""Phase 31 — stop_resident removes from registry; double-stop raises.

R1 PB-10 lock (strict; cleanup wraps in try/except).
"""

from __future__ import annotations

import pytest

from mindsos_capacity import ResidentError

from ._fixtures import make_layer_with_test_monitor


def test_stop_removes_from_active():
    layer, monitor_iri = make_layer_with_test_monitor()
    sub = layer.start_resident(monitor_iri)
    assert sub in layer.active_subscriptions()
    layer.stop_resident(sub)
    assert sub not in layer.active_subscriptions()
    assert layer.active_subscriptions() == []


def test_stop_marks_inactive():
    layer, monitor_iri = make_layer_with_test_monitor()
    sub = layer.start_resident(monitor_iri)
    layer.stop_resident(sub)
    assert sub.is_active() is False


def test_double_stop_raises_resident_error():
    """R1 PB-10 — strict (parent shape)."""
    layer, monitor_iri = make_layer_with_test_monitor()
    sub = layer.start_resident(monitor_iri)
    layer.stop_resident(sub)
    with pytest.raises(ResidentError):
        layer.stop_resident(sub)


def test_stop_wrong_type_raises_resident_error():
    layer, _ = make_layer_with_test_monitor()
    with pytest.raises(ResidentError):
        layer.stop_resident("not-a-subscription")
