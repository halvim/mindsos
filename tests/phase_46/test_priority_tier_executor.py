"""Phase 46 — priority-tier Executor (ADR-0163 / D32.5b/c)."""

from __future__ import annotations

import threading

from mindsos_capacity.tiers import TierEnum
from mindsos_intelligence.cancellation import CancelToken
from mindsos_intelligence.executor import PriorityTierExecutor, default_worker_count


def _noop():
    return None


def test_four_tier_ordering():
    ex = PriorityTierExecutor(max_workers=1)
    ex.submit(_noop, tier=TierEnum.DREAM, task_id="d")
    ex.submit(_noop, tier=TierEnum.BACKGROUND, task_id="b")
    ex.submit(_noop, tier=TierEnum.CRITICAL, task_id="c")
    ex.submit(_noop, tier=TierEnum.FOREGROUND, task_id="f")
    assert ex.pending_order() == ["c", "f", "b", "d"]


def test_within_tier_score_ordering():
    ex = PriorityTierExecutor(max_workers=1)
    ex.submit(_noop, tier=TierEnum.FOREGROUND, task_id="lo", score=100)
    ex.submit(_noop, tier=TierEnum.FOREGROUND, task_id="hi", score=900)
    ex.submit(_noop, tier=TierEnum.FOREGROUND, task_id="mid", score=500)
    assert ex.pending_order() == ["hi", "mid", "lo"]


def test_submit_order_is_final_tiebreaker():
    ex = PriorityTierExecutor(max_workers=1)
    ex.submit(_noop, tier=TierEnum.BACKGROUND, task_id="first", score=100)
    ex.submit(_noop, tier=TierEnum.BACKGROUND, task_id="second", score=100)
    assert ex.pending_order() == ["first", "second"]


def test_write_priority_reorders():
    ex = PriorityTierExecutor(max_workers=1)
    ex.submit(_noop, tier=TierEnum.BACKGROUND, task_id="a", score=100)
    ex.submit(_noop, tier=TierEnum.BACKGROUND, task_id="b", score=200)
    assert ex.pending_order() == ["b", "a"]
    ex.write_priority("a", score=900)
    assert ex.pending_order() == ["a", "b"]


def test_elevate_top_of_new_tier():
    ex = PriorityTierExecutor(max_workers=1)
    ex.submit(_noop, tier=TierEnum.FOREGROUND, task_id="a", score=500)
    ex.submit(_noop, tier=TierEnum.FOREGROUND, task_id="b", score=500)
    ex.write_priority("a", tier=TierEnum.CRITICAL)
    order = ex.pending_order()
    assert order[0] == "a"


def test_default_worker_count_bounded():
    assert 1 <= default_worker_count() <= 8


def test_runs_submitted_task():
    ex = PriorityTierExecutor(max_workers=2)
    ex.start()
    fut = ex.submit(lambda: 21 * 2, tier=TierEnum.FOREGROUND, task_id="calc")
    assert fut.result(timeout=5) == 42
    ex.shutdown()


def test_auto_preempt_on_elevation_cancels_running():
    ex = PriorityTierExecutor(max_workers=1)
    started = threading.Event()
    release = threading.Event()
    token = CancelToken()

    def background():
        started.set()
        while not token.is_set():
            if release.wait(0.02):
                return "completed"
        return "cancelled"

    fut = ex.submit(
        background, tier=TierEnum.BACKGROUND, task_id="bg", cancel_token=token
    )
    ex.start()
    assert started.wait(5)
    ex.submit(_noop, tier=TierEnum.CRITICAL, task_id="crit")
    assert fut.result(timeout=5) == "cancelled"
    assert token.is_set() is True
    ex.shutdown()
