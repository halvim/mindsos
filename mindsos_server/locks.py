"""
Server-layer module-level locks.

Phase 24 ships two lock primitives per ADR-0006 §amendment-1 (Phase
24 rename ratification):

* :data:`RELEASE_SHIP_LOCK` — module-level ``threading.RLock`` that
  serializes :func:`mindsos_server.release.release_update` invocations.
  Renamed from ``GLOBAL_PROMOTE_LOCK`` per ADR-0118 §"Consequences" +
  ADR-0006 §am1; held only inside ``release_update``, never on the
  per-promotion ``propose_for_promotion`` path. Phase 24 design log
  PB-12(a) lock: ``threading.RLock`` substrate (matches Phase 06's
  original §Decision §2; v1 is single-process per ADR-0129 §Rationale
  so threading primitive is sufficient; SQLite advisory considered +
  rejected at PB-12(a) — the multi-role FalkorDB-copy loop is the
  protected critical section, not the SQLite write).

  ``release_update`` body acquires RLock outer; SQLite-side write
  uses Phase 22 :func:`mindsos_server.admin.admin_tx` BEGIN IMMEDIATE
  inner (two primitives at two stores' scope; matches shipped Phase
  22 pattern).

* :class:`UserMutexRegistry` — declared per ADR-0006 §am1 retention.
  The original §Decision §1 per-user mutex registry stays; Phase 24
  has no consumer (no cross-user state is touched inside
  ``release_update`` per ADR-0118 §"Decision" §2). First consumer is
  Phase 25 cross-user read substrate
  (``read_other_local()`` per ADR-0008 §am1).

ADR cross-references: ADR-0006 §am1 (Phase 24 rename ratification);
ADR-0118 §"Decision" §2 (RELEASE_SHIP_LOCK scope); ADR-0129
§Rationale (single-process v1); Phase 24 design log PB-12(a).
"""

from __future__ import annotations

import threading
from typing import AbstractSet, ContextManager, Iterable


#: Module-level RLock serializing :func:`mindsos_server.release.
#: release_update`. Renamed from ``GLOBAL_PROMOTE_LOCK`` per ADR-0006
#: §am1; substrate ``threading.RLock`` per Phase 24 design log PB-
#: 12(a). Acquired at ``release_update`` function entry; released on
#: exit (success OR failure — try/finally pattern).
#:
#: Reentrancy (RLock vs Lock) is cheap insurance per ADR-0006
#: §Rationale "the orchestrator and its helpers are layered; the
#: same thread may need to re-enter the same lock."
RELEASE_SHIP_LOCK: threading.RLock = threading.RLock()


class UserMutexRegistry:
    """Per-user ``threading.RLock`` registry per ADR-0006 §Decision §1.

    Lazily creates one :class:`threading.RLock` per ``user_id`` on
    first ask. :meth:`user_mutexes` returns a context manager that
    acquires the requested locks in lexicographic order (deterministic
    deadlock avoidance per ADR-0006 §Rationale) and releases in
    reverse on exit.

    **Phase 24 status:** declared, **no consumer**. First consumer is
    Phase 25's cross-user read substrate (``read_other_local()``
    context manager per ADR-0008 §am1). Declared at Phase 24 per ADR-
    0006 §am1 retention clause — the per-user mutex contract holds
    even at v1 zero-consumer state; future consumers wire here without
    a Phase 24 retrofit.

    The Phase 24 :func:`mindsos_server.release.release_update` does
    NOT acquire per-user mutexes — no cross-user state is touched per
    ADR-0118 §"Decision" §2 (release-ship copies pending_global →
    canonical_global; both are admin-curated Global graphs, not user
    Locals).
    """

    def __init__(self) -> None:
        self._mutexes: dict[str, threading.RLock] = {}
        self._registry_lock = threading.Lock()

    def get(self, user_id: str) -> threading.RLock:
        """Return the :class:`threading.RLock` for ``user_id`` (lazy-creates).

        Thread-safe registry-insertion guard via
        :attr:`_registry_lock`; the returned RLock is independent.
        """
        with self._registry_lock:
            mutex = self._mutexes.get(user_id)
            if mutex is None:
                mutex = threading.RLock()
                self._mutexes[user_id] = mutex
            return mutex

    def user_mutexes(
        self, user_ids: Iterable[str]
    ) -> ContextManager[AbstractSet[str]]:
        """Acquire the per-user mutexes for ``user_ids`` in lex order.

        Returns a context manager that:

        1. Sorts ``user_ids`` lexicographically (per ADR-0006
           §Decision §1 — deterministic order avoids deadlock).
        2. Acquires each lock in order.
        3. Releases in reverse on exit.

        Yields the frozenset of acquired user_ids for caller
        diagnostic use (e.g., logging which users a transient install
        covered).

        **Phase 24 note:** This context manager is declared per ADR-
        0006 §am1 retention; no Phase 24 callsite invokes it. Phase
        25's ``read_other_local()`` is the first consumer per ADR-
        0008 §am1.
        """
        sorted_ids = sorted(set(user_ids))

        class _UserMutexes:
            def __init__(self, registry: UserMutexRegistry, ids: list[str]) -> None:
                self._registry = registry
                self._ids = ids
                self._acquired: list[threading.RLock] = []

            def __enter__(self) -> frozenset[str]:
                for uid in self._ids:
                    mutex = self._registry.get(uid)
                    mutex.acquire()
                    self._acquired.append(mutex)
                return frozenset(self._ids)

            def __exit__(self, exc_type, exc_val, exc_tb) -> None:
                # Release in REVERSE order of acquisition.
                while self._acquired:
                    mutex = self._acquired.pop()
                    mutex.release()

        return _UserMutexes(self, sorted_ids)


__all__ = [
    "RELEASE_SHIP_LOCK",
    "UserMutexRegistry",
]
