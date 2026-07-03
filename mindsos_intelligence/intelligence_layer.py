"""IntelligenceLayer lifecycle + dream-cycle timer (ADR-0163..0169 /
Chat A R1 D32 / ADR-0162).

One IntelligenceLayer per session. ``start`` wires the substrate
(priority-tier Executor + worker pool, signal-triage thread, Monitor
subscription registry, ALS registry, Mental Model); ``enqueue`` submits
a unit of work to the Executor; ``stop(mode="abort")`` cooperatively
cancels in-flight work and tears the substrate down. ``mode="pause"`` is
deferred (Push 5) and raises ``NotImplementedError``.

The dream-cycle timer ships the timer mechanism + the MM deep-copy
primitive (``fork_dream_mm``); the dream driver it ticks (invoke dream
bodies -> directives -> live re-execution + ALS firing) is supplied at
Phase 47/48 — at Phase 46 it is an injected callback (default absent).
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional

from mindsos_capacity.tiers import TierEnum

from .als_registry import ALSSubsystemRegistry
from .cancellation import CancelToken
from .executor import PriorityTierExecutor
from .mm import MentalModel
from .monitor_subscription import MonitorSubscriptionRegistry
from .resources import ResourceLedger
from .signal_triage import SignalTriageWorker
from .submind import SubMind
from .submind_arbiter import SubMindArbiter
from .submind_registry import SubMindRegistry


class DreamCycleTimer:
    def __init__(self, interval_s: float, driver: Callable[[], None]) -> None:
        self._interval = interval_s
        self._driver = driver
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="l4-dream-cycle", daemon=True
        )
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                self._driver()
            except BaseException:  # noqa: BLE001 — a dream tick must not kill the timer
                pass

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()


class IntelligenceLayer:
    def __init__(
        self,
        session: Any,
        *,
        knowledge: Any,
        capacity: Any,
        max_workers: Optional[int] = None,
        dream_interval_s: Optional[float] = None,
        dream_driver: Optional[Callable[[], None]] = None,
        checkpoint_store: Any = None,
    ) -> None:
        self._session = session
        self._kl = knowledge
        self._cl = capacity
        self._checkpoint_store = checkpoint_store
        self._session_id = getattr(session, "session_id", "session")
        self._user_id = getattr(session, "user_id", "user")
        # feat/subminds Slice 2: the exclusive-resource ledger feeds the
        # SubMind arbiter's contention check + event-driven resume. Wired
        # into the executor so running tasks' held resources are tracked.
        self._resource_ledger = ResourceLedger()
        self._executor = PriorityTierExecutor(
            max_workers=max_workers, resource_ledger=self._resource_ledger
        )
        self._submind_arbiter: Optional[SubMindArbiter] = None
        self._triage = SignalTriageWorker()
        self._als = ALSSubsystemRegistry()
        self._dream_interval_s = dream_interval_s
        self._dream_driver = dream_driver
        self._mm: Optional[MentalModel] = None
        self._monitors: Optional[MonitorSubscriptionRegistry] = None
        self._subminds: Optional[SubMindRegistry] = None
        self._dream_timer: Optional[DreamCycleTimer] = None
        self._cancel_tokens: Dict[str, CancelToken] = {}
        self._task_seq = 0
        self._started = False
        self._stopped = False
        self._lock = threading.Lock()

    @property
    def mm(self) -> MentalModel:
        if self._mm is None:
            raise RuntimeError("IntelligenceLayer not started")
        return self._mm

    @property
    def executor(self) -> PriorityTierExecutor:
        return self._executor

    @property
    def signal_triage(self) -> SignalTriageWorker:
        return self._triage

    @property
    def als_registry(self) -> ALSSubsystemRegistry:
        return self._als

    @property
    def monitor_registry(self) -> MonitorSubscriptionRegistry:
        if self._monitors is None:
            raise RuntimeError("IntelligenceLayer not started")
        return self._monitors

    @property
    def submind_registry(self) -> SubMindRegistry:
        if self._subminds is None:
            raise RuntimeError("IntelligenceLayer not started")
        return self._subminds

    @property
    def resource_ledger(self) -> ResourceLedger:
        return self._resource_ledger

    def endow(self, submind: SubMind) -> None:
        """Endow this session's Mind with a SubMind (feat/subminds Slice 1).

        Convenience pass-through to the per-session ``SubMindRegistry``;
        valid only after ``start()``. Authored/Global definitions are
        loaded from the L2 ``subminds`` role-graph by the registry; this
        path is the runtime-object entry used by tests and the taught
        path (later slice)."""
        self.submind_registry.endow(submind)

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            if self._stopped:
                raise RuntimeError("IntelligenceLayer cannot restart after stop")
            self._mm = MentalModel(
                session_id=self._session_id, user_id=self._user_id
            )
            self._monitors = MonitorSubscriptionRegistry()
            self._monitors.load_from(self._cl)
            self._executor.start()
            self._triage.start()
            # feat/subminds (Slice 1/2): the per-session SubMind lifecycle
            # owner + the resource-contention arbiter. Empty by default —
            # inert until a SubMind is endowed and emits a Signal.
            from .dispatch import L4Dispatcher
            from mindsos_capacity.exceptions import PipelineNotFoundError
            from mindsos_capacity.pipeline import find_pipeline

            dispatcher = L4Dispatcher(
                self._cl, session=self._session, kl=self._kl, mm_handle=self._mm
            )

            def _plan(start, goal):
                # The resolver is a goal: build a pipeline to it from the
                # currently-available capabilities. A None start seeds the
                # search with the goal itself (a real start datastate is an
                # endowment concern, Slice 4).
                return find_pipeline(
                    self._cl,
                    session=self._session,
                    start_datastate=(start if start is not None else goal),
                    target_datastate=goal,
                )

            self._submind_arbiter = SubMindArbiter(
                self._executor,
                dispatcher,
                self._resource_ledger,
                plan_fn=_plan,
                pipeline_not_found=PipelineNotFoundError,
            )
            self._submind_arbiter.install_on_ledger()
            self._subminds = SubMindRegistry(
                self._triage, self._executor, arbiter=self._submind_arbiter
            )
            self._subminds.start()
            # Crash recovery (ADR-0179 / D-B50): scan for unconsolidated
            # checkpoint markers left by a prior crashed session and write a
            # ``crash_marker`` Episode for each. No-op when no store is wired.
            if self._checkpoint_store is not None:
                from . import crash_recovery
                from .dispatch import L4Dispatcher

                recovery_dispatcher = L4Dispatcher(
                    self._cl, session=self._session, kl=self._kl
                )
                crash_recovery.recover_unconsolidated(
                    self._checkpoint_store, recovery_dispatcher
                )
            if self._dream_driver is not None and self._dream_interval_s is not None:
                self._dream_timer = DreamCycleTimer(
                    self._dream_interval_s, self._dream_driver
                )
                self._dream_timer.start()
            self._started = True

    def enqueue(
        self,
        task: Callable[[], object],
        *,
        tier: TierEnum = TierEnum.FOREGROUND,
        task_id: Optional[str] = None,
        score: Optional[int] = None,
        held_resources=(),
    ):
        if not self._started:
            raise RuntimeError("IntelligenceLayer not started")
        if self._stopped:
            raise RuntimeError("IntelligenceLayer is stopped")
        if task_id is None:
            self._task_seq += 1
            task_id = f"task-{self._task_seq}"
        token = CancelToken()
        self._cancel_tokens[task_id] = token
        # ``held_resources`` (default empty) declares the exclusive
        # resources this task holds while running, for the SubMind arbiter's
        # contention check (ADR-0189 §2). Empty = no holds = unchanged from
        # the shipped behavior.
        return self._executor.submit(
            task,
            tier=tier,
            task_id=task_id,
            score=score,
            cancel_token=token,
            held_resources=held_resources,
        )

    def fork_dream_mm(self) -> MentalModel:
        return self.mm.deep_copy()

    def stop(self, mode: str = "abort") -> None:
        if mode == "pause":
            raise NotImplementedError(
                "IntelligenceLayer.stop(mode='pause') is deferred post-v1 "
                "(Push 5); v1 supports mode='abort' only"
            )
        if mode != "abort":
            raise ValueError(f"unknown stop mode {mode!r}")
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
            for token in self._cancel_tokens.values():
                token.request_cancel()
            if self._subminds is not None:
                self._subminds.stop()
            if self._dream_timer is not None:
                self._dream_timer.stop()
            self._triage.stop()
            self._executor.shutdown(wait=True)


__all__ = ["IntelligenceLayer", "DreamCycleTimer"]
