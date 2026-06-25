"""L4 exclusive-resource model (ADR-0189 §2 / ADR-0188 §10).

The one-time *resource model* the SubMind arbitration needs and the
Slice-3 Reflex seizure path reuses. "resource" means an
**exclusive/contended** resource — an actuator, a single-holder lock, a
command stream — **not** shared schedulable compute. Preempt-vs-reconcile
is *derived* from contention over these resources, not declared.

A :class:`ResourceLedger` records which running task holds which
resources and answers "is this set contended, and by whom". Holds are
registered when a task starts running and released when it finishes (the
executor brackets the run-loop); releasing fires an ``on_release``
callback so a parked, resource-blocked need can resume **event-driven**
(the unsatisfiable-need policy, ADR-0189 §3).

Each :class:`ResourceHold` carries a ``cancel`` callable — the
*cooperative* preemption hook used in Slice 2 (request the holder to
yield at its next checkpoint). Slice 3's Reflex path adds a forcible
*seize* hook on the same record (supersede, not negotiate); the ledger
shape is designed to host it without change.

Pure L4: stdlib only, no upward import — safe on the Py3.10 sandbox.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, Optional, Tuple


@dataclass(frozen=True)
class ResourceHold:
    """A running task's claim on a set of exclusive resources.

    ``tier`` is the integer ``TierEnum`` value (lower = more urgent) and
    ``score`` the attention score — together they let the arbiter decide
    whether an incoming need outranks the holder. ``cancel`` is the
    cooperative-cancel hook (Slice 2); a forcible ``seize`` hook is added
    by the Slice-3 Reflex path.
    """

    task_id: str
    resources: FrozenSet[str]
    tier: int
    score: int
    cancel: Optional[Callable[[], None]] = None


@dataclass(frozen=True)
class Contention:
    """Result of a contention query over a resource set.

    ``free`` is True when no running hold overlaps the queried resources.
    ``conflicts`` is the de-duplicated tuple of overlapping holds (a hold
    may cover several queried resources but appears once).
    """

    free: bool
    conflicts: Tuple[ResourceHold, ...] = ()


class ResourceLedger:
    """Thread-safe map of exclusive resource → current holding task.

    Touched by executor worker threads (``acquire``/``release``) and the
    arbiter's triage thread (``contention``), so all access is locked.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_resource: Dict[str, ResourceHold] = {}
        self._by_task: Dict[str, ResourceHold] = {}
        self._on_release: Optional[Callable[[FrozenSet[str], str], None]] = None

    def set_on_release(
        self, callback: Optional[Callable[[FrozenSet[str], str], None]]
    ) -> None:
        """Register the single resume hook: ``callback(freed_resources,
        task_id)`` fired after each release. The arbiter uses it to wake
        parked needs blocked on a now-free resource."""
        with self._lock:
            self._on_release = callback

    def acquire(
        self,
        task_id: str,
        resources: FrozenSet[str],
        *,
        tier: int,
        score: int,
        cancel: Optional[Callable[[], None]] = None,
    ) -> Optional[ResourceHold]:
        """Record a hold. Exclusive resources map to one holder; the
        arbiter clears contention *before* a task is dispatched, so this
        records unconditionally (last-writer for a contended resource is
        a caller bug, not the ledger's to police). No-op for an empty
        resource set (returns ``None``)."""
        rs = frozenset(resources)
        if not rs:
            return None
        hold = ResourceHold(
            task_id=task_id, resources=rs, tier=tier, score=score, cancel=cancel
        )
        with self._lock:
            self._by_task[task_id] = hold
            for r in rs:
                self._by_resource[r] = hold
        return hold

    def release(self, task_id: str) -> FrozenSet[str]:
        """Drop a task's hold and fire ``on_release`` with the freed
        resources. Returns the freed set (empty if the task held
        nothing)."""
        with self._lock:
            hold = self._by_task.pop(task_id, None)
            if hold is None:
                return frozenset()
            freed = hold.resources
            for r in freed:
                # Only clear if this task is still the recorded holder.
                if self._by_resource.get(r) is hold:
                    del self._by_resource[r]
            callback = self._on_release
        if callback is not None and freed:
            callback(freed, task_id)
        return freed

    def holder_of(self, resource: str) -> Optional[ResourceHold]:
        with self._lock:
            return self._by_resource.get(resource)

    def contention(self, resources: FrozenSet[str]) -> Contention:
        """Which running holds overlap ``resources`` (de-duplicated)."""
        rs = frozenset(resources)
        if not rs:
            return Contention(free=True)
        with self._lock:
            seen_ids: set[str] = set()
            conflicts = []
            for r in rs:
                hold = self._by_resource.get(r)
                if hold is not None and hold.task_id not in seen_ids:
                    seen_ids.add(hold.task_id)
                    conflicts.append(hold)
        return Contention(free=not conflicts, conflicts=tuple(conflicts))


__all__ = ["ResourceHold", "Contention", "ResourceLedger"]
