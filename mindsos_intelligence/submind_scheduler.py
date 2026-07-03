"""SubMindScheduler — the single L4-owned resident loop (ADR-0188 / ADR-0189 §4).

This is the **partial reversal of ADR-0155**: resident, self-firing
monitor loops return — but as one L4-owned scheduler thread, **not** the
deleted L3 ``start_resident``/``stop_resident`` lifecycle. ADR-0155's
L3-purity holds (no loop in ``mindsos_capacity``); the loop lives here in
``mindsos_intelligence``.

One thread owns *when*: a timer-heap of next-fire times. It sleeps until
the earliest due SubMind, ticks it (via the injected ``on_due``
callback), then reschedules at that SubMind's new adaptive interval
(``SubMind.next_interval``). Cheap checks run inline on this thread;
heavy checks are the registry's concern to offload to the Phase-46 worker
pool. Thread-per-SubMind is rejected — it does not scale (design log §14).

The scheduler is mechanism only: it knows nothing about Signals, tiers,
or the executor. ``on_due(submind)`` (supplied by the registry) does the
tick + emission. Time + sleep are injectable for deterministic tests.
"""

from __future__ import annotations

import heapq
import itertools
import threading
import time
from typing import Callable, List, Optional, Tuple

from .submind import SubMind


class SubMindScheduler:
    def __init__(
        self,
        on_due: Callable[[SubMind], None],
        *,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._on_due = on_due
        self._time = time_fn
        self._heap: List[Tuple[float, int, SubMind]] = []
        self._seq = itertools.count()
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    # ── membership ──────────────────────────────────────────────────────

    def add(self, submind: SubMind, *, delay: Optional[float] = None) -> None:
        """Schedule ``submind``'s first tick at ``now + delay`` (default =
        its current adaptive interval)."""
        when = self._time() + (
            submind.next_interval() if delay is None else delay
        )
        with self._cv:
            heapq.heappush(self._heap, (when, next(self._seq), submind))
            self._cv.notify()

    def __len__(self) -> int:
        with self._lock:
            return len(self._heap)

    # ── lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="l4-submind-scheduler", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._cv:
            self._cv.notify_all()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── loop ────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop.is_set():
            with self._cv:
                while not self._heap and not self._stop.is_set():
                    self._cv.wait()
                if self._stop.is_set():
                    return
                when, _seq, submind = self._heap[0]
                now = self._time()
                if when > now:
                    # Not due yet — sleep until due or a sooner add/stop.
                    self._cv.wait(timeout=when - now)
                    continue
                heapq.heappop(self._heap)
            # Outside the lock: tick is isolated so one bad check-capacity
            # never kills the scheduler (dream-timer precedent).
            try:
                self._on_due(submind)
            except BaseException:  # noqa: BLE001
                pass
            # Reschedule at the new adaptive interval.
            self.add(submind)


__all__ = ["SubMindScheduler"]
