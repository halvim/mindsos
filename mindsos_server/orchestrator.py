"""
Server-side orchestrator for cross-user-read operations.

Phase 25 first ship. Houses:

* :func:`read_other_local` — admin context manager that opens a
  refcount-installed transient view of another user's Local Metagraph
  for diagnostic reads (ADR-0008 §Decision). Never flushes on
  teardown (I-S3).
* :class:`InstallRecord` — per-user install bookkeeping (ADR-0008
  §Decision verbatim).
* Module-level state:
    * :data:`_installed_locals` — the ``dict[str, InstallRecord]``
      registry. Module-level per PB-38 ("free-function orchestrator;
      class defers").
    * :data:`_install_lock` — guards :data:`_installed_locals` against
      cross-thread races (PB-41 saturation lock).
    * :data:`_mutex_registry` — :class:`UserMutexRegistry` first
      consumer (ADR-0006 §amendment-2 + PB-22).

Surface stays free-function per PB-38. The :class:`MindsOSServer`
class first-construction is deferred to the first user-Local-write
phase per ADR-0011 §amendment-1 §1.2 + PB-37.

Persister + KL are passed per-call via kwargs (PB-40, Phase 22
``admin_tx(conn)`` precedent). No module-level singleton; the CLI
helpers :func:`_resolve_persister` + :func:`_resolve_kl` in
``mindsos_cli/commands/server.py`` construct fresh instances per CLI
invocation.

The refcount-bump branch is **test-only at v1 production** — the
single-process CLI per-command-process model means no concurrent
``read_other_local`` callers in the same process can exist outside
tests. The branch is exercised via
``tests/phase_25/test_read_other_local_refcount_bump_in_process.py``
(in-process nested ``with`` invocations) per ADR-0008 §amendment-1.

See ``confirmation_docs/PHASE_25_DESIGN_LOG.md`` §5 + §4 for the
round-by-round rationale chain.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Mapping, Optional, Tuple

from mindsos_core import Metagraph
from mindsos_knowledge import KnowledgeLayer

from mindsos_server.audit import EVT_CROSS_USER_READ_INSTALL, write_audit
from mindsos_server.authz import _require_or_audit
from mindsos_server.capabilities import CAN_READ_OTHER_LOCALS
from mindsos_server.locks import UserMutexRegistry
from mindsos_server.persistence import LocalPersister
from mindsos_server.session import Session

__all__ = [
    "InstallRecord",
    "read_other_local",
    "reset_state_for_tests",
]


# ─────────────────────────────────────────────────────────────────────
# InstallRecord — ADR-0008 §Decision verbatim
# ─────────────────────────────────────────────────────────────────────


@dataclass
class InstallRecord:
    """
    Per-user install bookkeeping. ADR-0008 §Decision verbatim.

    Attributes:
        user_id: Stored on the record for symmetric dict iteration
            (the dict key is also ``user_id`` — denormalized for
            iter ergonomics).
        installed_by_session: ``session_id`` that triggered the
            install, or ``None`` for transient admin/promote installs.
            v1 always ``None`` per PB-37 (login/logout install path
            collapsed; only transient admin reads exist).
        transient: ``True`` → :func:`_release` skips persister.save
            on refcount→0 teardown (I-S3 invariant). ``False`` → a
            sticky install that flushes on extract (forward shape;
            unreachable at v1).
        refcount: Concurrent-reader count. Each :func:`read_other_local`
            entry increments; each exit decrements; record is dropped
            when refcount→0.
    """

    user_id: str
    installed_by_session: Optional[str]
    transient: bool
    refcount: int


# ─────────────────────────────────────────────────────────────────────
# Module-level state — PB-38 (free functions) + PB-40 (no global init)
# ─────────────────────────────────────────────────────────────────────

#: Registry of currently-installed Locals per ADR-0008.
#: Keyed by ``user_id``. Mutate ONLY through :func:`_install_for` and
#: :func:`_release`; tests reset via :func:`reset_state_for_tests`.
_installed_locals: dict[str, InstallRecord] = {}

#: Coarse lock guarding :data:`_installed_locals` against cross-thread
#: races during refcount bookkeeping. PB-41 saturation lock.
_install_lock: threading.Lock = threading.Lock()

#: Per-user mutex registry (ADR-0006 §amendment-2 first consumer).
#: :func:`read_other_local` acquires the target user's mutex during
#: the ctx-mgr lifetime; future promotion orchestrator acquires N
#: mutexes in lex order across N author user_ids.
_mutex_registry: UserMutexRegistry = UserMutexRegistry()


def reset_state_for_tests() -> None:
    """
    Reset module-level state to a pristine baseline.

    Used by ``tests/phase_25/conftest.py``'s autouse fixture per
    PB-R6-03 (Round 6 pre-impl re-analysis lock). Resets both
    :data:`_installed_locals` and :data:`_mutex_registry` so per-test
    isolation matches the per-CLI-invocation isolation invariant in
    production.

    Never call from production code — there is no live use case for
    runtime state-reset at v1.
    """
    global _installed_locals, _mutex_registry
    with _install_lock:
        _installed_locals = {}
    _mutex_registry = UserMutexRegistry()


# ─────────────────────────────────────────────────────────────────────
# Public ctx mgr — read_other_local
# ─────────────────────────────────────────────────────────────────────


@contextmanager
def read_other_local(
    conn: sqlite3.Connection,
    admin_session: Session,
    target_user_id: str,
    *,
    persister: LocalPersister,
    kl: KnowledgeLayer,
) -> Iterator[Metagraph]:
    """
    Admin reads ``target_user_id``'s Local with refcount-install per
    ADR-0008.

    Lifecycle:

    1. Gate on :data:`CAN_READ_OTHER_LOCALS` (PERMISSION_DENIED audit
       row + raise on deny).
    2. Acquire the target's per-user mutex (PB-22).
    3. :func:`_install_for` — if no install exists, hydrate via
       ``persister.load`` (or lazy-create empty via
       ``kl.local_metagraph`` if no dump exists), install into KL,
       record ``transient=True, refcount=1``. If an install exists,
       bump refcount; reuse the existing Metagraph.
    4. Emit one :data:`EVT_CROSS_USER_READ_INSTALL` audit row;
       commit (PB-R7-02 — Phase 21 admin_query_audit pattern).
    5. Yield the Metagraph to the caller.
    6. On exit, :func:`_release` decrements refcount; on refcount→0
       extracts from KL and (because ``transient=True``) DOES NOT
       call ``persister.save`` (I-S3 — admin reads never flush).

    PB-43: self-target allowed (degenerate case; admins occasionally
    read their own Local through this code path for symmetry — saves
    the caller a branch).

    PB-31: single audit row at acquire; the release is implicit (no
    EVT_CROSS_USER_READ_RELEASE — release symmetry is bookkeeping,
    not audit-worthy at v1).

    Args:
        conn: SQLite connection for the cap-check audit row +
            EVT_CROSS_USER_READ_INSTALL audit row.
        admin_session: Caller's :class:`Session`. MUST hold
            ``CAN_READ_OTHER_LOCALS``.
        target_user_id: ``user_id`` whose Local to install + yield.
        persister: :class:`LocalPersister` for dump load. Phase 25 v1
            production uses :class:`InMemoryLocalPersister` (always
            empty per CLI per-command-process model).
        kl: :class:`KnowledgeLayer` instance the install goes into.

    Raises:
        PermissionDeniedError: ``admin_session`` lacks the capability.

    Yields:
        The target's Local :class:`Metagraph`.
    """
    _require_or_audit(
        conn,
        admin_session,
        CAN_READ_OTHER_LOCALS,
        verb="read_other_local",
    )

    with _mutex_registry.user_mutexes([target_user_id]):
        mg, was_existing, refcount_after = _install_for(
            target_user_id,
            transient=True,
            persister=persister,
            kl=kl,
        )

        write_audit(
            conn,
            actor=admin_session.user_id,
            event=EVT_CROSS_USER_READ_INSTALL,
            target=target_user_id,
            extra={
                "admin_user_id": admin_session.user_id,
                "target_user_id": target_user_id,
                "transient": True,
                "install_was_existing": was_existing,
                "refcount_after_acquire": refcount_after,
                "target_role_graph_node_counts": _node_counts(mg),
            },
        )
        # PB-R7-02 — commit the audit row immediately. write_audit per
        # ADR-0013 leaves commit to the caller; the Phase 21
        # admin_query_audit pattern is "write_audit + commit". Without
        # an explicit commit a read-only summary flow would silently
        # drop the audit row on connection close.
        conn.commit()

        try:
            yield mg
        finally:
            _release(target_user_id, persister=persister, kl=kl)


# ─────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────


def _install_for(
    user_id: str,
    *,
    transient: bool,
    persister: LocalPersister,
    kl: KnowledgeLayer,
) -> Tuple[Metagraph, bool, int]:
    """
    Bump-or-install for ``user_id``.

    Returns ``(metagraph, was_existing, refcount_after_acquire)``.

    PB-R6-04 — when no persister dump exists, use ``kl.local_metagraph``
    to lazy-create the Metagraph with the canonical
    ``local_knowledge:<user_id>`` name + auto-ensured Local-named role
    graphs. The previous design-log shape minted a raw Metagraph with
    ``name=f"local_{user_id}"`` which would break a future SQLite
    persister's graph-name keying.
    """
    with _install_lock:
        existing = _installed_locals.get(user_id)
        if existing is not None:
            existing.refcount += 1
            # Sticky upgrade per ADR-0008 — if a transient install is
            # bumped by a sticky caller, the record loses its transient
            # bit. At v1 every caller is transient (PB-37), so this is
            # dead code for production but exercised in tests via
            # synthetic InstallRecord construction.
            if not transient and existing.transient:
                existing.transient = False
            mg = kl.local_metagraph(user_id)
            return mg, True, existing.refcount

        dump = persister.load(user_id)
        if dump is None:
            # Cold start, no dump on disk. KL's lazy-create gives us
            # the canonically-named Metagraph + auto-ensured roles —
            # symmetric with first-session install at the future
            # user-Local-write phase.
            mg = kl.local_metagraph(user_id)
        else:
            # Dump on disk; hand it to KL via the install hook.
            kl.install_local_metagraph(user_id, dump)
            mg = dump

        _installed_locals[user_id] = InstallRecord(
            user_id=user_id,
            installed_by_session=None,
            transient=transient,
            refcount=1,
        )
        return mg, False, 1


def _release(
    user_id: str,
    *,
    persister: LocalPersister,
    kl: KnowledgeLayer,
) -> None:
    """
    Decrement refcount; tear down + (conditionally) flush on
    refcount→0.

    Transient records (``transient=True``) skip ``persister.save`` on
    teardown — that is invariant I-S3 (admin reads never flush).
    Sticky records call ``persister.save``; failure re-installs and
    re-raises so the caller can retry (forward shape; unreachable at
    v1 per PB-37).
    """
    with _install_lock:
        record = _installed_locals.get(user_id)
        if record is None:
            return
        record.refcount -= 1
        if record.refcount > 0:
            return

        mg = kl.extract_local_metagraph(user_id)
        if not record.transient:
            # v1 dead code per PB-37 (no sticky installs ever exist
            # in this code path — read_other_local always asks for
            # transient=True). Forward shape for the first user-
            # Local-write phase whose logout-flush + promotion-flush
            # callers raise sticky records.
            try:
                persister.save(user_id, mg)
            except Exception:
                # Rollback per ADR-0011 §"On logout" — re-install
                # then re-raise so the caller's exception handler
                # sees the failure.
                kl.install_local_metagraph(user_id, mg)
                record.refcount = 1
                raise

        del _installed_locals[user_id]


def _node_counts(mg: Metagraph) -> Mapping[str, int]:
    """
    Per-role node-count for the audit payload.

    PB-R6-02 — :class:`Metagraph` has no ``graphs_by_role`` attribute;
    role lookup is via iterating ``mg.graphs.values()`` and reading
    each Graph's ``role`` attribute. Returns a dict role → node-count
    (graphs with ``role is None`` are skipped — there are none in a
    KL-managed Local Metagraph, but defensive against future
    metagraph shapes).
    """
    counts: dict[str, int] = {}
    for g in mg.graphs.values():
        if g.role is None:
            continue
        counts[g.role] = len(g.nodes)
    return counts
