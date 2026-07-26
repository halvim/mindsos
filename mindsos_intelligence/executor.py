"""Priority-tier Executor + worker pool (ADR-0163 / Chat A D32.5b/c).

A custom Executor over a priority heap keyed ``(tier, -attention_score,
submit_seq)``. Tier dominates (``TierEnum`` is int-valued, CRITICAL
lowest); within-tier ordered by descending attention_score; submit order
is the final tiebreaker. Queue-priority ordering, not running-task
preemption — preemption is cooperative: a higher-priority arrival that
outranks a running task by more than the hysteresis margin calls
``request_cancel`` on that task's token (the worker releases at its next
yield).

``write_priority(request_id, score=None, tier=None)`` is the single v1
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
        "request_id",
        "fn",
        "cancel_token",
        "future",
        "live",
        "held_resources",
    )

    def __init__(
        self, tier, score, seq, request_id, fn, cancel_token, future, held_resources=()
    ):
        self.tier = tier
        self.score = score
        self.seq = seq
        self.request_id = request_id
        self.fn = fn
        self.cancel_token = cancel_token
        self.future = future
        self.live = True
        self.held_resources = frozenset(held_resources)

    def key(self):
        return (int(self.tier), -self.score, self.seq)

    def __lt__(self, other):
        return self.key() < other.key()


class PriorityTierExecutor:
    def __init__(
        self,
        max_workers: Optional[int] = None,
        hysteresis: int = DEFAULT_HYSTERESIS,
        *,
        resource_ledger=None,
    ) -> None:
        self._max_workers = max_workers or default_worker_count()
        self._hysteresis = hysteresis
        # Optional L4 exclusive-resource ledger (feat/subminds Slice 2). When
        # wired, a running task's ``held_resources`` are registered while it
        # runs and released on completion — feeding the SubMind arbiter's
        # contention check + event-driven resume. Default None = no-op, so
        # the shipped behavior (and every existing caller) is unchanged.
        self._resource_ledger = resource_ledger
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
        request_id: str,
        score: Optional[int] = None,
        cancel_token=None,
        preempt: bool = True,
        held_resources=(),
    ) -> Future:
        # ``preempt`` (default True = shipped behavior) gates the
        # tier/score cooperative-cancel of outranked running work. The
        # SubMind path passes ``preempt=False``: its preemption is decided
        # by resource contention in the arbiter, not blindly by tier
        # (ADR-0189 §1 — tier is decoupled from preemption). ``held_
        # resources`` are registered in the ledger while the task runs.
        if score is None:
            score = default_score(tier)
        fut: Future = Future()
        with self._lock:
            if self._shutdown:
                raise RuntimeError("PriorityTierExecutor is shut down")
            entry = _Entry(
                tier, score, next(self._seq), request_id, fn, cancel_token, fut,
                held_resources,
            )
            self._pending[request_id] = entry
            heapq.heappush(self._heap, entry)
            if preempt:
                self._maybe_preempt_locked(entry)
            self._not_empty.notify()
        return fut

    def write_priority(
        self,
        request_id: str,
        score: Optional[int] = None,
        tier: Optional[TierEnum] = None,
    ) -> None:
        with self._lock:
            entry = self._pending.get(request_id)
            if entry is None:
                running = self._running.get(request_id)
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
                request_id,
                entry.fn,
                entry.cancel_token,
                entry.future,
                entry.held_resources,
            )
            self._pending[request_id] = replacement
            heapq.heappush(self._heap, replacement)
            self._maybe_preempt_locked(replacement)
            self._not_empty.notify()

    def pending_order(self) -> List[str]:
        with self._lock:
            return [e.request_id for e in sorted(self._pending.values())]

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
            if entry.live and self._pending.get(entry.request_id) is entry:
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
                self._pending.pop(entry.request_id, None)
                self._running[entry.request_id] = entry
            if not entry.future.set_running_or_notify_cancel():
                with self._lock:
                    self._running.pop(entry.request_id, None)
                continue
            # Register exclusive-resource holds for the duration of the run
            # (acquire/release fire no executor-lock callbacks, but release
            # invokes the ledger's resume hook → arbiter → submit, so it
            # must run OUTSIDE self._lock to avoid re-entrant deadlock).
            if self._resource_ledger is not None and entry.held_resources:
                cancel = (
                    entry.cancel_token.request_cancel
                    if entry.cancel_token is not None
                    else None
                )
                self._resource_ledger.acquire(
                    entry.request_id,
                    entry.held_resources,
                    tier=int(entry.tier),
                    score=entry.score,
                    cancel=cancel,
                )
            try:
                entry.future.set_result(entry.fn())
            except BaseException as exc:  # noqa: BLE001 — surfaced on the Future
                entry.future.set_exception(exc)
            finally:
                with self._lock:
                    self._running.pop(entry.request_id, None)
                if self._resource_ledger is not None and entry.held_resources:
                    self._resource_ledger.release(entry.request_id)


__all__ = ["PriorityTierExecutor", "default_worker_count"]
