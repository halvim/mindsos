"""Phase 46 — MonitorSubscriptionRegistry (ADR-0168)."""

from __future__ import annotations

import threading

import pytest

from mindsos_intelligence.monitor_subscription import MonitorSubscriptionRegistry


class FakeMonitor:
    def __init__(self, iri, subscribes_to):
        self.iri = iri
        self.subscribes_to = tuple(subscribes_to)


class FakeCL:
    def __init__(self, monitors):
        self._monitors = monitors

    def iter_monitors(self):
        return list(self._monitors)


def test_load_from_inverts_subscribes_to():
    cl = FakeCL(
        [
            FakeMonitor("capacity:mon:a", ["datastate:r.level", "datastate:r.temp"]),
            FakeMonitor("capacity:mon:b", ["datastate:r.level"]),
        ]
    )
    reg = MonitorSubscriptionRegistry()
    reg.load_from(cl)
    assert len(reg) == 2
    assert reg.monitors_for("datastate:r.level") == ["capacity:mon:a", "capacity:mon:b"]
    assert reg.monitors_for("datastate:r.temp") == ["capacity:mon:a"]
    assert reg.monitors_for("datastate:none") == []


def test_unregister_removes_subscriptions():
    reg = MonitorSubscriptionRegistry()
    reg.register(FakeMonitor("capacity:mon:a", ["datastate:r.level"]))
    reg.unregister("capacity:mon:a")
    assert len(reg) == 0
    assert reg.monitors_for("datastate:r.level") == []


def test_register_off_orchestrator_thread_raises():
    reg = MonitorSubscriptionRegistry()
    err = []

    def worker():
        try:
            reg.register(FakeMonitor("capacity:mon:x", ["datastate:r.level"]))
        except RuntimeError as exc:
            err.append(exc)

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert len(err) == 1
