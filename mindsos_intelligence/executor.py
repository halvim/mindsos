"""Priority-tier Executor + worker pool (ADR-0163 / Chat A D32.5b/c).

A custom Executor over a priority heap keyed ``(tier, -attention_score,
submit_seq)``. Tier dominates (``TierEnum`` is int-valued, CRITICAL
lowest); within-tier ordered by descending attention_score; submit order
is the final tiebreaker. Queue-priority ordering, not running-task
preemption — preemption is cooperative: a higher-priority arrival that
outranks a running task by more than the hysteresis margin calls
``request_cancel`` on that task's token (the worker releases at its next
yield).

``write_priority(task_id, score=None, tier=None)`` is the single v1
mutation primitive (PB-1): ``score`` and/or ``tier`` change a pending
task; ``score=None`` with a ``tier`` is the "top of new tier" elevate
default. The L3-invoking ``update_priority`` wrapper + the MM
write-through land at Phase 47/48.
"""

from __future__ import annotations

import heapq
import itertools
import os
import threading
from concurrent.futures import Future
from typing import Callable, Dict, List, Optional

from mindsos_capacity.tiers import DEFAULT_HYSTERESIS, TierEnum, default_score


def default_worker_count() -> int:
    return min(8, os.cpu_count() or 1)


class _Entry:
    __slots__ = (
        "tier",
        "score",
        "seq",
        "task_id",
        "fn",
        "cancel_token",
        "future",
        "live",
    )

    def __init__(self, tier, score, seq, task_id, fn, cancel_token, future):
        self.tier = tier
        self.score = score
        self.seq = seq
        self.task_id = task_id
        self.fn = fn
        self.cancel_token = cancel_token
        self.future = future
        self.live = True

    def key(self):
        return (int(self.tier), -self.score, self.seq)

    def __lt__(self, other):
        return self.key() < other.key()


class PriorityTierExecutor:
    def __init__(
        self,
        max_workers: Optional[int] = None,
        hysteresis: int = DEFAULT_HYSTERESIS,
    ) -> None:
        self._max_workers = max_workers or default_worker_count()
        self._hysteresis = hysteresis
        self._heap: List[_Entry] = []
        self._pending: Dict[str, _Entry] = {}
        self._running: Dict[str, _Entry] = {}
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._seq = itertools.count()
        self._workers: List[threading.Thread] = []
        self._started = False
        self._shutdown = False

    @property
    def max_workers(self) -> int:
        return self._max_workers

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            for i in range(self._max_workers):
                t = threading.Thread(
                    target=self._worker_loop, name=f"l4-worker-{i}", daemon=True
                )
                t.start()
                self._workers.append(t)

    def submit(
        self,
        fn: Callable[[], object],
        *,
        tier: TierEnum,
        task_id: str,
        score: Optional[int] = None,
        cancel_token=None,
    ) -> Future:
        if score is None:
            score = default_score(tier)
        fut: Future = Future()
        with self._lock:
            if self._shutdown:
                raise RuntimeError("PriorityTierExecutor is shut down")
            entry = _Entry(tier, score, next(self._seq), task_id, fn, cancel_token, fut)
            self._pending[task_id] = entry
            heapq.heappush(self._heap, entry)
            self._maybe_preempt_locked(entry)
            self._not_empty.notify()
        return fut

    def write_priority(
        self,
        task_id: str,
        score: Optional[int] = None,
        tier: Optional[TierEnum] = None,
    ) -> None:
        with self._lock:
            entry = self._pending.get(task_id)
            if entry is None:
                running = self._running.get(task_id)
                if running is not None:
                    if tier is not None:
                        running.tier = tier
                    if score is not None:
                        running.score = score
                return
            new_tier = tier if tier is not None else entry.tier
            if score is None and tier is not None:
                new_score = self._top_of_tier_locked(new_tier)
            elif score is None:
                new_score = entry.score
            else:
                new_score = score
            entry.live = False
            replacement = _Entry(
                new_tier,
                new_score,
                next(self._seq),
                task_id,
                entry.fn,
                entry.cancel_token,
                entry.future,
            )
            self._pending[task_id] = replacement
            heapq.heappush(self._heap, replacement)
            self._maybe_preempt_locked(replacement)
            self._not_empty.notify()

    def pending_order(self) -> List[str]:
        with self._lock:
            return [e.task_id for e in sorted(self._pending.values())]

    def shutdown(self, wait: bool = True) -> None:
        with self._lock:
            self._shutdown = True
            self._not_empty.notify_all()
        if wait:
            for t in self._workers:
                t.join()

    def _top_of_tier_locked(self, tier: TierEnum) -> int:
        scores = [e.score for e in self._pending.values() if e.live and e.tier == tier]
        scores += [e.score for e in self._running.values() if e.tier == tier]
        return (max(scores) + 1) if scores else default_score(tier)

    def _maybe_preempt_locked(self, arrival: _Entry) -> None:
        for running in self._running.values():
            if running.cancel_token is None:
                continue
            outranks = int(arrival.tier) < int(running.tier) or (
                arrival.tier == running.tier
                and arrival.score > running.score + self._hysteresis
            )
            if outranks:
                running.cancel_token.request_cancel()

    def _pop_live_locked(self) -> Optional[_Entry]:
        while self._heap:
            entry = heapq.heappop(self._heap)
            if entry.live and self._pending.get(entry.task_id) is entry:
                return entry
        return None

    def _has_live_locked(self) -> bool:
        return any(e.live for e in self._pending.values())

    def _worker_loop(self) -> None:
        while True:
            with self._not_empty:
                while True:
                    if self._shutdown and not self._has_live_locked():
                        return
                    entry = self._pop_live_locked()
                    if entry is not None:
                        break
                    self._not_empty.wait()
                self._pending.pop(entry.task_id, None)
                self._running[entry.task_id] = entry
            if not entry.future.set_running_or_notify_cancel():
                with self._lock:
                    self._running.pop(entry.task_id, None)
                continue
            try:
                entry.future.set_result(entry.fn())
            except BaseException as exc:  # noqa: BLE001 — surfaced on the Future
                entry.future.set_exception(exc)
            finally:
                with self._lock:
                    self._running.pop(entry.task_id, None)


__all__ = ["PriorityTierExecutor", "default_worker_count"]
