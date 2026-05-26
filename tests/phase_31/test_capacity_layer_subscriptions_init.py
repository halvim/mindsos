"""Phase 31 — CapacityLayer.__init__ initializes self._subscriptions = {}.

R1 PB-9 lock — private attribute, accessed via methods only. This test
asserts on the attribute directly to lock the ctor contract (otherwise
tests rely entirely on method behavior).
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer


def test_subscriptions_dict_present_on_init():
    layer = CapacityLayer()
    assert hasattr(layer, "_subscriptions")
    assert layer._subscriptions == {}


def test_subscriptions_is_dict_type():
    layer = CapacityLayer()
    assert isinstance(layer._subscriptions, dict)


def test_two_layers_have_independent_registries():
    """Per-layer registry (ADR-0073 §am-1 clause 1) — closes §Cost row."""
    layer_a = CapacityLayer()
    layer_b = CapacityLayer()
    layer_a._subscriptions["fake_id"] = object()
    assert "fake_id" in layer_a._subscriptions
    assert "fake_id" not in layer_b._subscriptions
