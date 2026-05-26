"""Phase 31 — active_subscriptions returns list snapshot of all active subs."""

from __future__ import annotations

from ._fixtures import make_layer_with_test_monitor, make_test_monitor


def test_active_subscriptions_empty_on_fresh_layer():
    layer, _ = make_layer_with_test_monitor()
    assert layer.active_subscriptions() == []


def test_active_subscriptions_returns_all_started():
    layer, iri_a = make_layer_with_test_monitor(name="resident.alpha")
    # Register a second Monitor (same DataState subscribe target).
    iri_b = "capacity:perception:resident.beta"
    layer.register_capacity(make_test_monitor(name="resident.beta"))
    sub_a = layer.start_resident(iri_a)
    sub_b = layer.start_resident(iri_b)
    actives = layer.active_subscriptions()
    assert set(actives) == {sub_a, sub_b}
    assert len(actives) == 2


def test_active_subscriptions_returns_list_copy():
    """R3 confirm — list copy, not live view."""
    layer, monitor_iri = make_layer_with_test_monitor()
    sub = layer.start_resident(monitor_iri)
    snapshot = layer.active_subscriptions()
    # Mutate snapshot; registry must be unaffected.
    snapshot.clear()
    assert sub in layer.active_subscriptions()
