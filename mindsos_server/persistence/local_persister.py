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
    "FalkorDBLocalPersister",
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


class FalkorDBLocalPersister:
    """FalkorDB-backed :class:`LocalPersister` (ADR-0160, Phase 44).

    Native round-trip — no serialization. A user's Local is the
    Metagraph named ``local_knowledge:<user_id>`` living in the shared
    FalkorDB graph alongside the Global; ``save`` / ``load`` reuse
    :class:`MetagraphRepository` / :class:`MetagraphLoader`. ``delete``
    is a scoped teardown keyed on the Local's ``metagraph_id`` (a
    blanket ``DETACH DELETE`` would destroy the co-resident Global and
    other users' Locals). ``save`` / ``delete`` hold the per-user mutex
    (ADR-0006) because Falkor lacks multi-statement atomicity.
    """

    def __init__(self, client, *, mutex_registry=None) -> None:
        from mindsos_server.locks import UserMutexRegistry

        self._client = client
        self._mutex = (
            mutex_registry if mutex_registry is not None else UserMutexRegistry()
        )

    def _metagraph_name(self, user_id: str) -> str:
        from mindsos_knowledge.knowledge_layer import _local_metagraph_name

        return _local_metagraph_name(user_id)

    def load(self, user_id: str) -> Optional[Metagraph]:
        from mindsos_core.reconstruction import MetagraphLoader

        loader = MetagraphLoader(self._client)
        metagraph_id = loader.find_by_name(self._metagraph_name(user_id))
        if metagraph_id is None:
            return None
        return loader.load(metagraph_id)

    def save(self, user_id: str, metagraph: Metagraph) -> None:
        from mindsos_core.exceptions import PersistenceError
        from mindsos_core.persistence import MetagraphRepository

        try:
            with self._mutex.user_mutexes([user_id]):
                MetagraphRepository(self._client).persist(metagraph)
        except PersistenceError as exc:
            raise FlushFailedError(user_id) from exc

    def delete(self, user_id: str) -> bool:
        from mindsos_core.reconstruction import MetagraphLoader

        with self._mutex.user_mutexes([user_id]):
            loader = MetagraphLoader(self._client)
            metagraph_id = loader.find_by_name(self._metagraph_name(user_id))
            if metagraph_id is None:
                return False
            gid_rows = self._client.run_query(
                "MATCH (m:Metagraph {id: $mid})<-[:IN_METAGRAPH]-(g:Graph) "
                "RETURN g.id AS gid",
                {"mid": metagraph_id},
            ).rows
            graph_ids = [row["gid"] for row in gid_rows]
            self._client.run_batch(
                [
                    (
                        "MATCH (g:Graph)<-[:IN_GRAPH]-(el) "
                        "WHERE g.id IN $gids DETACH DELETE el",
                        {"gids": graph_ids},
                    ),
                    (
                        "MATCH (t:Tombstone) WHERE t.graph_id IN $gids "
                        "DETACH DELETE t",
                        {"gids": graph_ids},
                    ),
                    (
                        "MATCH (x:XRef {source_metagraph_id: $mid}) "
                        "DETACH DELETE x",
                        {"mid": metagraph_id},
                    ),
                    (
                        "MATCH (m:Metagraph {id: $mid})--(sat) "
                        "WHERE NOT sat:Graph DETACH DELETE sat",
                        {"mid": metagraph_id},
                    ),
                    (
                        "MATCH (m:Metagraph {id: $mid})<-[:IN_METAGRAPH]-(g:Graph) "
                        "DETACH DELETE g",
                        {"mid": metagraph_id},
                    ),
                    (
                        "MATCH (m:Metagraph {id: $mid}) DETACH DELETE m",
                        {"mid": metagraph_id},
                    ),
                ]
            )
            return True

    def reset_run_state(self, user_id: str) -> bool:
        """Wipe a Local's run-state, retaining its durable learning.

        ADR-0187 (F9-C reset boundary). Unlike :meth:`delete` (a full
        hard teardown that drops every graph AND the Metagraph node),
        reset is role-scoped: it ``DETACH DELETE``\\ s only the
        *elements* contained in the run-state role-graphs, leaving the
        (now-empty) graph nodes, the durable role-graphs, and the
        Metagraph node in place — so the Local stays well-formed and
        re-loadable.

        * **Wiped (run-state):** ``episodic_memories`` (per-task/run
          history), ``parameter-staging`` + ``pending-promotions``
          (in-flight ALS evidence/proposals — PB-A).
        * **Retained (durable learning):** ``learned-parameters`` +
          ``capacity-state`` — and every other graph.

        Returns ``True`` if the user's Local existed, ``False`` otherwise
        (idempotent — mirrors :meth:`delete`). Holds the per-user mutex
        (ADR-0006) because Falkor lacks multi-statement atomicity.
        """
        from mindsos_core.reconstruction import MetagraphLoader
        from mindsos_knowledge import (
            ROLE_EPISODIC_MEMORIES,
            ROLE_PARAMETER_STAGING,
            ROLE_PENDING_PROMOTIONS,
        )

        run_state_roles = [
            ROLE_EPISODIC_MEMORIES,
            ROLE_PARAMETER_STAGING,
            ROLE_PENDING_PROMOTIONS,
        ]
        with self._mutex.user_mutexes([user_id]):
            loader = MetagraphLoader(self._client)
            metagraph_id = loader.find_by_name(self._metagraph_name(user_id))
            if metagraph_id is None:
                return False
            gid_rows = self._client.run_query(
                "MATCH (m:Metagraph {id: $mid})<-[:IN_METAGRAPH]-(g:Graph) "
                "WHERE g.role IN $roles RETURN g.id AS gid",
                {"mid": metagraph_id, "roles": run_state_roles},
            ).rows
            graph_ids = [row["gid"] for row in gid_rows]
            if not graph_ids:
                return True
            # Reuse only the per-graph element-delete subset of delete()
            # (the elements + their tombstones), scoped to run-state
            # graph ids. The graph nodes + Metagraph node are NOT dropped.
            self._client.run_batch(
                [
                    (
                        "MATCH (g:Graph)<-[:IN_GRAPH]-(el) "
                        "WHERE g.id IN $gids DETACH DELETE el",
                        {"gids": graph_ids},
                    ),
                    (
                        "MATCH (t:Tombstone) WHERE t.graph_id IN $gids "
                        "DETACH DELETE t",
                        {"gids": graph_ids},
                    ),
                ]
            )
            return True
