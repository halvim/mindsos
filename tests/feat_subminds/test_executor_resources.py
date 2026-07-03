"""feat/subminds Slice 2 — executor additive changes.

Backward-compat (default preempt unchanged) + the optional resource
ledger bracketing a running task's holds + the preempt=False gate.
"""

from __future__ import annotations

import threading
import time

from mindsos_capacity.tiers import TierEnum
from mindsos_intelligence.cancellation import CancelToken
from mindsos_intelligence.executor import PriorityTierExecutor
from mindsos_intelligence.resources import ResourceLedger


def test_held_resources_registered_during_run_and_released():
    led = ResourceLedger()
    ex = PriorityTierExecutor(max_workers=1, resource_ledger=led)
    ex.start()
    started = threading.Event()
    release = threading.Event()

    def work():
        started.set()
        release.wait(2.0)
        return "done"

    try:
        fut = ex.submit(
            work, tier=TierEnum.FOREGROUND, task_id="t1", held_resources=("arm",)
        )
        assert started.wait(2.0)
        # hold visible while running
        assert led.holder_of("arm") is not None
        release.set()
        assert fut.result(2.0) == "done"
        # released after completion
        deadline = time.time() + 2.0
        while led.holder_of("arm") is not None and time.time() < deadline:
            time.sleep(0.01)
        assert led.holder_of("arm") is None
    finally:
        ex.shutdown(wait=True)


def test_preempt_false_does_not_cancel_running_lower_priority():
    ex = PriorityTierExecutor(max_workers=1)
    ex.start()
    started = threading.Event()
    release = threading.Event()
    token = CancelToken()

    def low():
        started.set()
        release.wait(2.0)
        return "low"

    try:
        fut_low = ex.submit(
            low, tier=TierEnum.BACKGROUND, task_id="low", cancel_token=token
        )
        assert started.wait(2.0)
        # a higher-tier arrival with preempt=False must NOT request cancel
        ex.submit(
            lambda: "hi", tier=TierEnum.CRITICAL, task_id="hi", preempt=False
        )
        time.sleep(0.05)
        assert not token.is_set()
        release.set()
        assert fut_low.result(2.0) == "low"
    finally:
        ex.shutdown(wait=True)


def test_preempt_true_still_cancels_running_lower_priority():
    ex = PriorityTierExecutor(max_workers=1)
    ex.start()
    started = threading.Event()
    release = threading.Event()
    token = CancelToken()

    def low():
        started.set()
        release.wait(2.0)
        return "low"

    try:
        ex.submit(low, tier=TierEnum.BACKGROUND, task_id="low", cancel_token=token)
        assert started.wait(2.0)
        # default path (preempt=True) preserves the shipped cooperative cancel
        ex.submit(lambda: "hi", tier=TierEnum.CRITICAL, task_id="hi")
        deadline = time.time() + 2.0
        while not token.is_set() and time.time() < deadline:
            time.sleep(0.01)
        assert token.is_set()
        release.set()
    finally:
        ex.shutdown(wait=True)
