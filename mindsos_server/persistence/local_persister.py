"""
:class:`LocalPersister` Protocol + :class:`InMemoryLocalPersister` impl.

Phase 25 first ship per ADR-0011 §amendment-2:

* **Protocol shape** uses :class:`mindsos_core.Metagraph` directly at
  v1; the ``MetagraphDump`` dataclass defers to the first phase that
  ships SQLite/FalkorDB persisters. Probing the persistence boundary
  with the live Core type avoids the speculative serialization-format
  decision until a real storage backend exists.
* :meth:`LocalPersister.delete` returns :class:`bool` (was ``None``
  in the original ADR-0011 §Decision shape) — consumed by Phase 25's
  ``EVT_HARD_DELETE_USER.extra_json[local_dump_existed]`` key per
  PB-39 so the audit reader can distinguish "user had a Local on
  disk" from "user had nothing to delete." Idempotent semantics: a
  missing dump returns ``False`` without raising.
* :class:`InMemoryLocalPersister` ships with the
  ``fail_save_for: set[str]`` test-fault-injection hook (PB-33). The
  SQLite + Falkor implementations defer alongside the first user-
  Local-write phase per ADR-0011 §amendment-2 §1.3 future scope.

The Protocol is :func:`typing.runtime_checkable` to support
``isinstance(p, LocalPersister)`` in test assertions; the runtime check
is structural (attribute presence only — not type signatures).
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from mindsos_core import Metagraph

from mindsos_server.errors import FlushFailedError

__all__ = [
    "LocalPersister",
    "InMemoryLocalPersister",
]


@runtime_checkable
class LocalPersister(Protocol):
    """
    Storage Protocol for per-user Local :class:`Metagraph` dumps.

    Three-method contract per ADR-0011 §Decision (revised §amendment-2):

    * :meth:`load` — return the persisted Local (or ``None`` if no
      dump exists for this user).
    * :meth:`save` — write the Local. Raises :class:`FlushFailedError`
      on failure; caller (server orchestrator at Phase 25) is
      responsible for the 2-step rollback (re-install into KL + bubble).
    * :meth:`delete` — best-effort remove. Returns ``True`` iff a dump
      was actually present (and removed); ``False`` if no dump existed.
      Idempotent — must not raise on missing.

    Phase 25 ships :class:`InMemoryLocalPersister` only.
    ``SQLiteLocalPersister`` + ``FalkorDBLocalPersister`` land at the
    first user-Local-write phase.
    """

    def load(self, user_id: str) -> Optional[Metagraph]: ...
    def save(self, user_id: str, metagraph: Metagraph) -> None: ...
    def delete(self, user_id: str) -> bool: ...


class InMemoryLocalPersister:
    """
    Dict-backed :class:`LocalPersister` for tests + v1 admin-diagnostic
    use.

    Holds user_id → Metagraph in a process-local dict. State does NOT
    survive process exit — Phase 25's CLI per-command-process model
    means each ``mindsos server admin read-local`` invocation
    constructs a fresh empty persister via the CLI's
    :func:`_resolve_persister` helper. The Phase 25 admin-diagnostic
    verb consequently observes empty Locals in production at v1; this
    is documented in ``PHASE_25_DESIGN_LOG.md`` §7 ("admin diagnostic
    verb on always-empty Locals" — substrate correct, utility thin).

    The ``fail_save_for: set[str]`` hook makes :meth:`save` raise
    :class:`FlushFailedError` for any ``user_id`` added to the set.
    Phase 25 tests use this to exercise the future logout-flush /
    promotion-flush error path before its first live consumer exists.
    """

    def __init__(self) -> None:
        self._store: dict[str, Metagraph] = {}
        #: Test-fault-injection — any ``user_id`` in this set causes
        #: :meth:`save` to raise :class:`FlushFailedError`. Mutate
        #: directly from tests.
        self.fail_save_for: set[str] = set()

    def load(self, user_id: str) -> Optional[Metagraph]:
        """Return the stored Metagraph for ``user_id``, or ``None``."""
        return self._store.get(user_id)

    def save(self, user_id: str, metagraph: Metagraph) -> None:
        """
        Persist ``metagraph`` for ``user_id``.

        Raises:
            FlushFailedError: ``user_id`` is in :attr:`fail_save_for`.
                The store is NOT mutated when the fault is injected.
        """
        if user_id in self.fail_save_for:
            raise FlushFailedError(user_id)
        self._store[user_id] = metagraph

    def delete(self, user_id: str) -> bool:
        """
        Remove the dump for ``user_id``. Returns whether a dump was
        present at delete time.

        Idempotent: missing ``user_id`` returns ``False`` without
        raising. Phase 25 PB-39 — the bool is consumed by
        ``EVT_HARD_DELETE_USER.extra_json[local_dump_existed]`` so
        the audit reader can distinguish "had Local on disk" from
        "had nothing."
        """
        return self._store.pop(user_id, None) is not None
