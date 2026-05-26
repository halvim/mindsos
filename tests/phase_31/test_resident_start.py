"""Phase 31 — start_resident returns a registered ResidentSubscription.

ADR-0073 §amendment-1 clause 1 (per-layer registry); R1 PB-9 lock.
"""

from __future__ import annotations

from mindsos_capacity import ResidentSubscription
from mindsos_capacity.builtins import DS_RAW_TEXT

from ._fixtures import make_layer_with_test_monitor


def test_start_resident_returns_subscription():
    layer, monitor_iri = make_layer_with_test_monitor()
    sub = layer.start_resident(monitor_iri)
    assert isinstance(sub, ResidentSubscription)
    assert isinstance(sub.subscription_id, str) and sub.subscription_id


def test_start_resident_registers_in_layer():
    layer, monitor_iri = make_layer_with_test_monitor()
    sub = layer.start_resident(monitor_iri)
    actives = layer.active_subscriptions()
    assert sub in actives
    assert len(actives) == 1


def test_subscribes_to_from_declaration_not_kwarg():
    """ADR-0073 §am-1 clause 2 — declaration is source of truth."""
    layer, monitor_iri = make_layer_with_test_monitor(
        subscribes=(DS_RAW_TEXT,)
    )
    sub = layer.start_resident(monitor_iri)
    assert sub.subscribes_to == (DS_RAW_TEXT,)
