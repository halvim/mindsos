"""feat/subminds Slice 1 — live sense → emit → triage → executor heap.

The whole point of the slice: the autonomy dimension runs end-to-end on
the shipped substrate (SignalTriageWorker passthrough + PriorityTier-
Executor heap) with a stub resolver. Also exercises the IntelligenceLayer
``endow`` path.
"""

from __future__ import annotations

import time

from mindsos_capacity.tiers import TierEnum
from mindsos_intelligence import (
    CadenceLaw,
    IntelligenceLayer,
    PriorityTierExecutor,
    SignalTriageWorker,
    SubMind,
    SubMindDefinition,
    SubMindRegistry,
    VitalDirection,
)

_BANDS = (
    (0.0, TierEnum.BACKGROUND),
    (0.6, TierEnum.FOREGROUND),
    (0.8, TierEnum.CRITICAL),
)


def _battery(box, interval=0.02):
    return SubMind(SubMindDefinition(
        name="battery", check=lambda: box["v"], direction=VitalDirection.LOW_BAD,
        safe=100.0, threshold=50.0, failure=0.0, severity_tier_bands=_BANDS,
        importance_weight=1000, cadence=CadenceLaw(interval, interval, interval * 10),
    ))


def test_signal_reaches_executor_heap_with_mapped_tier_and_score():
    triage = SignalTriageWorker()
    executor = PriorityTierExecutor(max_workers=2)
    executor.start()
    triage.start()
    reg = SubMindRegistry(triage, executor)
    reg.endow(_battery({"v": 10.0}))   # severity 0.8 ⇒ CRITICAL, score 800
    reg.start()
    try:
        deadline = time.time() + 5
        while not reg.dispatched and time.time() < deadline:
            time.sleep(0.01)
    finally:
        reg.stop()
        triage.stop()
        executor.shutdown(wait=True)

    assert len(reg.emitted_signals) >= 1
    assert len(reg.dispatched) >= 1
    signal, tier = reg.dispatched[0]
    assert tier is TierEnum.CRITICAL
    assert signal.attention_score == 800


def test_storm_suppression_holds_under_live_loop():
    triage = SignalTriageWorker()
    executor = PriorityTierExecutor(max_workers=1)
    executor.start()
    triage.start()
    reg = SubMindRegistry(triage, executor)
    reg.endow(_battery({"v": 40.0}))   # steady distress, one tier
    reg.start()
    try:
        time.sleep(0.3)                # many ticks at 0.02s
    finally:
        reg.stop()
        triage.stop()
        executor.shutdown(wait=True)
    # Edge-triggered: a single crossing emits once despite ~15 ticks.
    assert len(reg.emitted_signals) == 1


def test_duplicate_endowment_rejected():
    triage = SignalTriageWorker()
    executor = PriorityTierExecutor(max_workers=1)
    reg = SubMindRegistry(triage, executor)
    reg.endow(_battery({"v": 80.0}))
    try:
        reg.endow(_battery({"v": 80.0}))
        assert False, "expected ValueError on duplicate name"
    except ValueError:
        pass


class _FakeSession:
    session_id = "s1"
    user_id = "u1"


class _FakeCL:
    def iter_monitors(self):
        return []


def test_intelligence_layer_endow_path():
    il = IntelligenceLayer(_FakeSession(), knowledge=None, capacity=_FakeCL())
    il.start()
    try:
        il.endow(_battery({"v": 10.0}))
        deadline = time.time() + 5
        reg = il.submind_registry
        while not reg.dispatched and time.time() < deadline:
            time.sleep(0.01)
        assert len(reg.dispatched) >= 1
        assert reg.dispatched[0][1] is TierEnum.CRITICAL
    finally:
        il.stop("abort")
