"""Phase 31 — ResidentSubscription is eq=False (handle semantics).

ADR-0073 §amendment-1 clause 3 — halvim divergence from parent's default
@dataclass eq.
"""

from __future__ import annotations

from ._fixtures import make_layer_with_test_monitor, make_test_monitor


def test_subscription_eq_is_identity_based():
    """Two distinct subs are never equal even if all fields match."""
    layer_a, monitor_iri_a = make_layer_with_test_monitor(name="resident.eqtest")
    layer_b, monitor_iri_b = make_layer_with_test_monitor(name="resident.eqtest")
    sub_a = layer_a.start_resident(monitor_iri_a)
    sub_b = layer_b.start_resident(monitor_iri_b)
    assert sub_a is not sub_b
    assert sub_a != sub_b  # eq=False → object identity


def test_subscription_equals_itself():
    layer, monitor_iri = make_layer_with_test_monitor()
    sub = layer.start_resident(monitor_iri)
    assert sub == sub


def test_subscription_hashable_by_id():
    """eq=False with default __hash__ → hashable via object id."""
    layer, monitor_iri = make_layer_with_test_monitor()
    sub_a = layer.start_resident(monitor_iri)
    layer.register_capacity(make_test_monitor(name="resident.eqtest_b"))
    sub_b = layer.start_resident("capacity:perception:resident.eqtest_b")
    s = {sub_a, sub_b}
    assert len(s) == 2
