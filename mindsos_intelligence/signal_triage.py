"""Signal-triage worker thread (ADR-0169 / D32.2=A).

Always-on dedicated thread that classifies incoming signals into the 4
priority tiers. The classifier is the L3 ``decision.signal_to_tier``
capacity (a Phase-47 skeleton); at Phase 46 the thread runs a
tier-passthrough stub so the signal -> tier -> queue path is genuinely
exercised. A constant-tier stub was rejected — CRITICAL would never
surface and the classification-path test would be vacuous.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable, Optional

from mindsos_capacity.tiers import TierEnum


def passthrough_classifier(signal: Any) -> TierEnum:
    """Phase-46 stub: route a tier hint carried on the signal; default
    FOREGROUND. Replaced by L3 ``decision.signal_to_tier`` at Phase 47."""
    tier = getattr(signal, "tier", None)
    if isinstance(tier, TierEnum):
        return tier
    if isinstance(signal, dict) and isinstance(signal.get("tier"), TierEnum):
        return signal["tier"]
    return TierEnum.FOREGROUND


class SignalTriageWorker:
    def __init__(
        self,
        classifier: Optional[Callable[[Any], TierEnum]] = None,
        on_classified: Optional[Callable[[Any, TierEnum], None]] = None,
    ) -> None:
        self._classifier = classifier or passthrough_classifier
        self._on_classified = on_classified
        self._queue: "queue.Queue[Any]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def submit_signal(self, signal: Any) -> None:
        self._queue.put(signal)

    def set_on_classified(
        self, on_classified: Optional[Callable[[Any, TierEnum], None]]
    ) -> None:
        """Set the post-classification sink (feat/subminds: the SubMind
        registry routes classified Signals onto the executor heap). Additive
        — the shipped default remains ``None`` until a consumer wires one."""
        self._on_classified = on_classified

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="l4-signal-triage", daemon=True
        )
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                signal = self._queue.get(timeout=0.05)
            except queue.Empty:
                continue
            tier = self._classifier(signal)
            if self._on_classified is not None:
                self._on_classified(signal, tier)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()


__all__ = ["SignalTriageWorker", "passthrough_classifier"]
