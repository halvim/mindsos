"""MonitorSubscriptionRegistry — L4-side Monitor lifecycle (ADR-0168 / D36).

Session-scope ``Dict[DataState IRI, List[Monitor IRI]]`` built by
inverting each Monitor's ``subscribes_to`` (the L3 producer
``cl.iter_monitors()`` shipped Phase 41 with no consumer). Reads (lookup
by changed DataState) are concurrent-safe; register/unregister are
orchestrator-thread-only (the explicit successor to the Phase-31 implicit
resident serialization).
"""

from __future__ import annotations

import threading
from typing import Dict, List


class MonitorSubscriptionRegistry:
    def __init__(self) -> None:
        self._by_datastate: Dict[str, List[str]] = {}
        self._monitors: Dict[str, object] = {}
        self._owner_thread = threading.get_ident()

    def _check_thread(self) -> None:
        if threading.get_ident() != self._owner_thread:
            raise RuntimeError(
                "MonitorSubscriptionRegistry register/unregister must run "
                "on the orchestrator thread"
            )

    def register(self, monitor: object) -> None:
        self._check_thread()
        iri = monitor.iri
        self._monitors[iri] = monitor
        for ds_iri in monitor.subscribes_to:
            subscribers = self._by_datastate.setdefault(ds_iri, [])
            if iri not in subscribers:
                subscribers.append(iri)

    def unregister(self, monitor_iri: str) -> None:
        self._check_thread()
        monitor = self._monitors.pop(monitor_iri, None)
        if monitor is None:
            return
        for ds_iri in monitor.subscribes_to:
            subscribers = self._by_datastate.get(ds_iri)
            if subscribers and monitor_iri in subscribers:
                subscribers.remove(monitor_iri)
                if not subscribers:
                    del self._by_datastate[ds_iri]

    def load_from(self, capacity_layer: object) -> None:
        for monitor in capacity_layer.iter_monitors():
            self.register(monitor)

    def monitors_for(self, datastate_iri: str) -> List[str]:
        return list(self._by_datastate.get(datastate_iri, ()))

    def __len__(self) -> int:
        return len(self._monitors)


__all__ = ["MonitorSubscriptionRegistry"]
