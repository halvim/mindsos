"""Phase 31 — ResidentSubscription on_signal / emit synchronous dispatch.

ADR-0073 — L3 holds the callable; L4 dispatches. Handlers run
synchronously; no threads or queues at L3.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import ResidentError

from ._fixtures import make_layer_with_test_monitor


def test_emit_calls_registered_handlers():
    layer, monitor_iri = make_layer_with_test_monitor()
    sub = layer.start_resident(monitor_iri)
    received = []
    sub.on_signal(lambda signal: received.append(signal))
    sub.emit({"signal": "test"})
    assert received == [{"signal": "test"}]


def test_emit_calls_multiple_handlers_in_order():
    layer, monitor_iri = make_layer_with_test_monitor()
    sub = layer.start_resident(monitor_iri)
    order = []
    sub.on_signal(lambda s: order.append(("first", s)))
    sub.on_signal(lambda s: order.append(("second", s)))
    sub.emit("hello")
    assert order == [("first", "hello"), ("second", "hello")]


def test_on_signal_after_stop_raises():
    layer, monitor_iri = make_layer_with_test_monitor()
    sub = layer.start_resident(monitor_iri)
    layer.stop_resident(sub)
    with pytest.raises(ResidentError):
        sub.on_signal(lambda s: None)


def test_emit_after_stop_raises():
    layer, monitor_iri = make_layer_with_test_monitor()
    sub = layer.start_resident(monitor_iri)
    layer.stop_resident(sub)
    with pytest.raises(ResidentError):
        sub.emit("anything")
