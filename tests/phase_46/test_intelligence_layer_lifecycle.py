"""Phase 46 — IntelligenceLayer lifecycle (ADR-0163 / Chat A R1 D32)."""

from __future__ import annotations

import threading

import pytest

from mindsos_capacity.tiers import TierEnum
from mindsos_intelligence.intelligence_layer import IntelligenceLayer


class FakeSession:
    session_id = "s1"
    user_id = "u1"


class FakeCL:
    def iter_monitors(self):
        return []


def _il(**kw):
    return IntelligenceLayer(
        FakeSession(), knowledge=None, capacity=FakeCL(), **kw
    )


def test_start_enqueue_stop_abort_roundtrip():
    il = _il(max_workers=2)
    il.start()
    fut = il.enqueue(lambda: 42)
    assert fut.result(timeout=5) == 42
    il.stop("abort")


def test_pause_raises_not_implemented():
    il = _il()
    il.start()
    with pytest.raises(NotImplementedError):
        il.stop("pause")
    il.stop("abort")


def test_enqueue_before_start_raises():
    il = _il()
    with pytest.raises(RuntimeError):
        il.enqueue(lambda: None)


def test_double_start_is_idempotent():
    il = _il()
    il.start()
    il.start()
    il.stop("abort")


def test_stop_abort_cancels_in_flight():
    il = _il(max_workers=1)
    started = threading.Event()
    token_holder = {}

    def blocking():
        started.set()
        il_token = list(il._cancel_tokens.values())[0]
        token_holder["t"] = il_token
        while not il_token.is_set():
            pass
        return "cancelled"

    il.start()
    fut = il.enqueue(blocking, tier=TierEnum.BACKGROUND)
    assert started.wait(5)
    il.stop("abort")
    assert fut.result(timeout=5) == "cancelled"


def test_fork_dream_mm_is_independent():
    il = _il()
    il.start()
    il.mm.root.request_run_ref = "requestrun:orig"
    fork = il.fork_dream_mm()
    assert fork.root.request_run_ref == "requestrun:orig"
    fork.root.outcome_ref = "outcome:x"
    assert il.mm.root.outcome_ref is None
    il.stop("abort")


def test_dream_cycle_timer_ticks_driver():
    ticks = []
    done = threading.Event()

    def driver():
        ticks.append(1)
        done.set()

    il = _il(dream_interval_s=0.05, dream_driver=driver)
    il.start()
    assert done.wait(5)
    il.stop("abort")
    assert len(ticks) >= 1
