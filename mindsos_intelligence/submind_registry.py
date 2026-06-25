"""SubMindRegistry — per-session lifecycle owner for endowed SubMinds (ADR-0189 §4).

Owns *which* SubMinds run and *their activation state*; delegates *when*
to the :class:`~mindsos_intelligence.submind_scheduler.SubMindScheduler`
and *deliberation* to L4. It is the single place the SubMind machinery
touches the shipped substrate:

    scheduler ── on_due ──▶ SubMind.tick() ──▶ Signal
                                                  │ submit_signal
                                                  ▼
                              SignalTriageWorker (passthrough)
                                                  │ on_classified(signal, tier)
                                                  ▼
                              PriorityTierExecutor.submit(stub_resolver,
                                                          tier, score)

Slice 1 dispatches a **stub resolver** onto the heap (the path runs live
— not a dead skeleton — but does no real work and no contention check).
Slice 2 replaces the stub with real resolver dispatch + the resource
model (preempt vs reconcile). Slice 3 adds the Reflex bypass.

Activation (ADR-0188 §6): ``ACTIVE`` (adaptive cadence), ``FLOORED``
(slow floor cadence — bounded blindness, not off), ``OFF`` (not ticked).
The scheduler keeps every endowed SubMind on its heap; FLOORED/OFF ride
the floor cadence and OFF ticks return ``None``.
"""

from __future__ import annotations

import itertools
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from mindsos_capacity.tiers import TierEnum

from .submind import ActivationState, SubMind, SubMindSignal, SubMindState
from .submind_scheduler import SubMindScheduler


def _default_resolver_factory(signal: SubMindSignal) -> Callable[[], object]:
    """Slice-1 stub: a no-op resolver that records the dispatch. Slice 2
    replaces this with real resolver dispatch + resource contention."""

    def _stub() -> dict:
        return {
            "submind": signal.submind_name,
            "tier": signal.tier,
            "severity": signal.severity,
            "kind": signal.kind,
            "stub": True,
        }

    return _stub


class SubMindRegistry:
    def __init__(
        self,
        triage: Any,
        executor: Any,
        *,
        arbiter: Any = None,
        resolver_factory: Callable[[SubMindSignal], Callable[[], object]] = (
            _default_resolver_factory
        ),
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._triage = triage
        self._executor = executor
        # Slice 2: when an arbiter is wired, classified Signals route through
        # it (real resolver dispatch + resource-contention preempt/reconcile
        # + unsatisfiable-need policy). With no arbiter the Slice-1 stub path
        # is preserved (a no-op resolver onto the heap) so the registry stays
        # usable standalone in tests.
        self._arbiter = arbiter
        self._resolver_factory = resolver_factory
        self._time = time_fn
        self._subminds: Dict[str, SubMind] = {}
        self._last_state: Dict[str, SubMindState] = {}
        self._scheduler: Optional[SubMindScheduler] = None
        self._seq = itertools.count()
        self._lock = threading.Lock()
        self._started = False
        self._stopped = False
        # Test/inspection visibility (not load-bearing).
        self.emitted_signals: List[SubMindSignal] = []
        self.dispatched: List[Tuple[SubMindSignal, TierEnum]] = []

    # ── membership ──────────────────────────────────────────────────────

    def endow(self, submind: SubMind) -> None:
        """Add a SubMind. If the registry is already running, schedule it."""
        with self._lock:
            if submind.name in self._subminds:
                raise ValueError(f"SubMind {submind.name!r} already endowed")
            self._subminds[submind.name] = submind
            sched = self._scheduler
        if sched is not None:
            sched.add(submind)

    def get(self, name: str) -> SubMind:
        return self._subminds[name]

    def __len__(self) -> int:
        return len(self._subminds)

    def set_activation(self, name: str, state: ActivationState) -> None:
        """L4 toggles a SubMind's activation (the orchestrator drives
        context-gating). The scheduler picks up the new cadence on the next
        reschedule."""
        self._subminds[name].activation = state

    # ── lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        if self._started:
            return
        if self._stopped:
            raise RuntimeError("SubMindRegistry cannot restart after stop")
        self._triage.set_on_classified(self._on_classified)
        self._scheduler = SubMindScheduler(self._on_due, time_fn=self._time)
        for submind in self._subminds.values():
            self._scheduler.add(submind)
        self._scheduler.start()
        self._started = True

    def stop(self) -> None:
        if self._stopped or not self._started:
            self._stopped = True
            return
        self._stopped = True
        if self._scheduler is not None:
            self._scheduler.stop()
        if self._arbiter is not None:
            try:
                self._arbiter.stop()
            except Exception:  # noqa: BLE001 — best-effort on teardown
                pass
        try:
            self._triage.set_on_classified(None)
        except Exception:  # noqa: BLE001 — best-effort unwire on teardown
            pass

    # ── the two seams ───────────────────────────────────────────────────

    def _on_due(self, submind: SubMind) -> None:
        """Scheduler callback: tick the SubMind, route any Signal to triage.

        Also detects the FIRED→ARMED recovery transition (the vital
        recovered) and tells the arbiter to clear the parked need — tier
        never decays, so nothing else would drop it (ADR-0189 §3). This
        reads the SubMind's public state and touches no frozen ``tick``
        contract."""
        prev = submind.state
        signal = submind.tick()
        if (
            self._arbiter is not None
            and prev is SubMindState.FIRED
            and submind.state is SubMindState.ARMED
        ):
            self._arbiter.clear(submind.name)
        if signal is None:
            return
        with self._lock:
            self.emitted_signals.append(signal)
        self._triage.submit_signal(signal)

    def _on_classified(self, signal: SubMindSignal, tier: TierEnum) -> None:
        """Triage callback. With an arbiter wired (Slice 2), hand the
        classified Signal to it for real resolver dispatch +
        resource-contention arbitration. Without one, fall back to the
        Slice-1 stub (a no-op resolver onto the executor heap)."""
        with self._lock:
            self.dispatched.append((signal, tier))
        if self._arbiter is not None:
            definition = self._subminds[signal.submind_name].definition
            self._arbiter.on_need(signal, tier, definition)
            return
        task_id = f"submind-{signal.submind_name}-{next(self._seq)}"
        self._executor.submit(
            self._resolver_factory(signal),
            tier=tier,
            task_id=task_id,
            score=signal.attention_score,
        )


__all__ = ["SubMindRegistry"]
