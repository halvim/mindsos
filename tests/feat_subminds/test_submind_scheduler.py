"""feat/subminds Slice 1 — SubMindScheduler timer-heap (ADR-0189 §4).

Deterministic via an injected time source where possible; one real
threaded fire for the loop. The scheduler is the L4-owned resident loop
that partially reverses ADR-0155.
"""

from __future__ import annotations

import threading
import time

from mindsos_capacity.tiers import TierEnum
from mindsos_intelligence import (
    CadenceLaw,
    SubMind,
    SubMindDefinition,
    SubMindScheduler,
    VitalDirection,
)

_BANDS = ((0.0, TierEnum.BACKGROUND), (0.8, TierEnum.CRITICAL))


def _sm(name, box, interval):
    return SubMind(SubMindDefinition(
        name=name, check=lambda: box["v"], direction=VitalDirection.LOW_BAD,
        safe=100.0, threshold=50.0, failure=0.0, severity_tier_bands=_BANDS,
        importance_weight=100, cadence=CadenceLaw(interval, interval, interval * 10),
    ))


def test_due_submind_is_ticked():
    fired = []
    done = threading.Event()

    def on_due(sm):
        fired.append(sm.name)
        done.set()

    sched = SubMindScheduler(on_due)
    sched.add(_sm("a", {"v": 40.0}, 0.02))
    sched.start()
    assert done.wait(5)
    sched.stop()
    assert "a" in fired
    assert not sched.is_alive()


def test_reschedules_repeatedly():
    counts = {"n": 0}
    enough = threading.Event()

    def on_due(sm):
        counts["n"] += 1
        if counts["n"] >= 3:
            enough.set()

    sched = SubMindScheduler(on_due)
    sched.add(_sm("a", {"v": 40.0}, 0.02))
    sched.start()
    assert enough.wait(5)
    sched.stop()
    assert counts["n"] >= 3


def test_earliest_fires_first():
    order = []
    seen = threading.Event()

    def on_due(sm):
        order.append(sm.name)
        if len(order) >= 2:
            seen.set()

    sched = SubMindScheduler(on_due)
    # 'fast' has a much shorter first delay than 'slow'.
    sched.add(_sm("slow", {"v": 40.0}, 0.5), delay=0.5)
    sched.add(_sm("fast", {"v": 40.0}, 0.02), delay=0.02)
    sched.start()
    time.sleep(0.1)
    sched.stop()
    assert order and order[0] == "fast"


def test_stop_is_clean_when_empty():
    sched = SubMindScheduler(lambda sm: None)
    sched.start()
    sched.stop()
    assert not sched.is_alive()
