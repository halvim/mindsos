"""Phase 31 — ResidentSubscription.state is the ADR-0099 Q6 slot.

L3 ships the field empty; L4 manages writes. R1 PB-11 lock — keep
the field at Phase 31 (named slot in ADR-0099).
"""

from __future__ import annotations

from ._fixtures import make_layer_with_test_monitor


def test_state_default_empty():
    layer, monitor_iri = make_layer_with_test_monitor()
    sub = layer.start_resident(monitor_iri)
    # L3 may seed sub.state['context'] when a session is supplied —
    # but with session=None (test path), context is None and state
    # remains empty (no provenance to stamp).
    assert sub.state == {}


def test_state_writable_by_caller():
    """L4 can write to the state slot; L3 never raises on writes."""
    layer, monitor_iri = make_layer_with_test_monitor()
    sub = layer.start_resident(monitor_iri)
    sub.state["test_key"] = "test_value"
    assert sub.state["test_key"] == "test_value"
