"""
mindsos_server.admin — admin verbs that operate on the user store + sessions table.

Phase 20 ships :func:`reset_admin` — the lock-out recovery escape hatch
per ADR-0012 + ADR-0012 §amendment-2. Phase 21 adds the audit-log
reader :func:`admin_query_audit` + :class:`AuditRow` per ADR-0013 +
ADR-0013 §amendment-2.

Pre-positions the ``admin.py`` module per Phase 20 PB-Z. Phase 22 will
add ``admin_promote_user``, ``admin_demote_user``, ``admin_disable_user``,
``admin_enable_user``, ``admin_kill_session``, ``hard_delete_user``
to this module + the ``_assert_not_sole_admin`` helper + ``LastAdminError``
class (deferred from Phase 20 per PB-B — no Phase 20 caller exists for
the helper).

Module conventions (inherited from Phase 18 ``users.py``):

* Functions take a ``conn: sqlite3.Connection`` as the first positional
  arg; callers control the transaction boundary by NOT-passing a
  pre-committed connection. ``reset_admin`` commits internally per
  PB-R single-tx lock; ``admin_query_audit`` commits the
  ``EVT_AUDIT_QUERY`` happy-path audit row at end-of-body per Phase 21
  PB-16.
* Argon2 parameters are injected as ``params=PRODUCTION_PARAMS`` kwarg
  (Phase 18 PB-14 convention); tests pass ``_TEST_FAST_PARAMS``.
* Audit actor for session-less verbs (reset-admin) is the OS user from
  ``pwd.getpwuid(os.getuid()).pw_name`` (Phase 18 bootstrap precedent;
  ADR-0012 §amendment-1). Session-backed verbs (admin_query_audit + all
  Phase 22 admin verbs) use ``session.user_id`` as actor.

See ``confirmation_docs/PHASE_20_DESIGN_LOG.md`` for Phase 20's 13-pick
rationale + ADR-0012 §amendment-2; ``confirmation_docs/PHASE_21_DESIGN_LOG.md``
for Phase 21's 20-pick rationale + ADR-0013 §amendment-2.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping

from contextlib import contextmanager
from typing import Iterator, Literal

from mindsos_server._argon2 import (
    PRODUCTION_PARAMS,
    Argon2Params,
    hash_password,
)
from mindsos_server.audit import (
    EVT_ADMIN_DEMOTE_USER,
    EVT_ADMIN_DISABLE_USER,
    EVT_ADMIN_ENABLE_USER,
    EVT_ADMIN_PROMOTE_USER,
    EVT_AUDIT_QUERY,
    EVT_HARD_DELETE_USER,
    EVT_KILL_SESSION,
    EVT_RESET_ADMIN,
    _now_utc_iso,
    write_audit,
)
from mindsos_server.authz import _require_or_audit
from mindsos_server.capabilities import (
    CAN_HARD_DELETE_ARCHIVED,
    CAN_KILL_SESSION,
    CAN_MANAGE_USERS,
    CAN_VIEW_AUDIT_LOG,
)
from mindsos_server.errors import (
    AlreadyAnAdminError,
    LastAdminError,
    NotAnAdminError,
    SessionNotFoundError,
    UserNotFoundError,
)
from mindsos_server.session import Session


@dataclass(frozen=True)
class ResetAdminResult:
    """
    Return type of :func:`reset_admin`.

    Tests + CLI ``--json`` payload + future audit reader (Phase 21)
    consume these three fields. ``sessions_killed`` is also denormalized
    into the ``EVT_RESET_ADMIN`` audit row's ``extra_json`` per PB-BB so
    the audit reader can answer "how many sessions were killed in user
    X's last reset" without joining ``EVT_KILL_SESSION`` rows.
    """

    user_id: str
    sessions_killed: int
    was_disabled: bool


def reset_admin(
    conn: sqlite3.Connection,
    user_id: str,
    new_password: str,
    *,
    os_user: str,
    params: Argon2Params = PRODUCTION_PARAMS,
) -> ResetAdminResult:
    """
    Rotate an existing admin's password + re-enable + kill sessions.

    Lock-out recovery per ADR-0012 §Decision + ADR-0012 §amendment-2.

    Pre-conditions (enforced in order):

    1. ``user_id`` must exist in ``users`` (else :class:`UserNotFoundError`
       per PB-A + PB-O).
    2. ``users.actor_role`` for that row must be ``'admin'`` (else
       :class:`NotAnAdminError` per PB-E + PB-N). Reset-admin will NEVER
       escalate a non-admin to admin — that path is :func:`admin_promote_user`
       (Phase 22), gated by ``CAN_MANAGE_USERS``.

    On success (all in a single SQLite transaction per PB-R, in the
    locked order ``DELETE → UPDATE → INSERT audits → commit``):

    * **DELETE** every row from ``sessions`` whose ``user_id`` matches.
      Captured first via SELECT for per-row audit emission. Killed
      tokens are unrecoverable.
    * **UPDATE** ``users``: replace ``password_hash`` with a fresh
      argon2id hash (fresh salt) at the given ``params``; force
      ``disabled = 0`` to re-enable a disabled-admin recovery target.
    * **INSERT** N× :data:`EVT_KILL_SESSION` audit rows (one per killed
      session) with ``extra = {"session_id": sid, "context":
      "reset_admin"}`` per PB-AA. Reuses the Phase 18-declared constant;
      first-fire of EVT_KILL_SESSION lifts from Phase 22 to Phase 20
      (PB-D). Phase 22 ``admin_kill_session`` is the second consumer.
    * **INSERT** 1× :data:`EVT_ADMIN_ENABLE_USER` audit row IFF the
      target was disabled, with ``extra = {"context": "reset_admin"}``
      per PB-U. First-fire also lifts to Phase 20.
    * **INSERT** 1× :data:`EVT_RESET_ADMIN` audit row with
      ``extra = {"was_disabled": bool, "sessions_killed": N}`` per
      PB-BB. The denormalized fields let Phase 21's audit reader
      answer reset-summary queries without joining.
    * **COMMIT**. Single-tx atomicity per PB-R closes the
      "UPDATE committed but DELETE didn't" crash-window where old
      tokens would silently authenticate against the new password.

    Audit ``actor`` is the OS user per ADR-0012 §Rationale ("filesystem
    access is the acceptable authority floor"). Reset-admin runs
    without a Session by definition — the operator's proof-of-authority
    is having shell access to ``server.db``.

    Args:
        conn: SQLite connection (typically from
            :func:`mindsos_server._db.open_db`). Must have schema v2 +
            ``PRAGMA foreign_keys=ON`` (Phase 18 PB-19 default).
        user_id: Target admin's user_id. Existence + admin-role checked.
        new_password: Plaintext; argon2id-hashed before UPDATE. Read
            by the CLI from stdin per PB-G (no ``--password`` flag).
        os_user: OS user invoking reset-admin (the CLI passes
            ``pwd.getpwuid(os.getuid()).pw_name``). Becomes
            ``actor_user`` on every audit row written by this verb.
        params: argon2id parameters. Defaults to
            :data:`PRODUCTION_PARAMS`; tests pass
            :data:`_TEST_FAST_PARAMS`. Mirrors Phase 18 PB-14
            convention for ``insert_user`` + ``_insert_first_admin``.

    Raises:
        UserNotFoundError: target ``user_id`` does not exist in ``users``.
        NotAnAdminError: target exists but ``actor_role != 'admin'``.

    Returns:
        :class:`ResetAdminResult` with ``user_id``, ``sessions_killed``
        (may be 0), and ``was_disabled`` (True iff the row's
        ``disabled`` column was 1 before the UPDATE).
    """
    # ---- Step 1: probe target (existence + role + disabled state). -----
    row = conn.execute(
        "SELECT actor_role, disabled FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        raise UserNotFoundError(user_id)
    actual_role, disabled_int = row[0], int(row[1])
    if actual_role != "admin":
        raise NotAnAdminError(user_id, actual_role)
    was_disabled = bool(disabled_int)

    # ---- Step 2: capture session_ids BEFORE delete (for per-row audit). --
    # SELECT-then-DELETE race in DELETE: same race as Phase 19
    # kill_my_own_sessions; CLI-only product → concurrency is one-shell
    # per invocation. Not opening a new vulnerability surface.
    rows = conn.execute(
        "SELECT session_id FROM sessions WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    session_ids = [r[0] for r in rows]

    # ---- Step 3: single transaction, DELETE-then-UPDATE order (PB-R). ---
    # Order matters: if UPDATE commits and DELETE doesn't, old tokens
    # would auth against the new password until the (now expired) row
    # exits via lazy expiry — strictly worse than the pre-reset state.
    # DELETE first ensures any partial-failure state is "sessions gone +
    # password unchanged" (operator can re-run reset-admin cleanly).
    conn.execute(
        "DELETE FROM sessions WHERE user_id = ?",
        (user_id,),
    )

    new_hash = hash_password(new_password, params=params)
    conn.execute(
        "UPDATE users SET password_hash = ?, disabled = 0 WHERE user_id = ?",
        (new_hash, user_id),
    )

    # ---- Step 4: audit rows (same transaction per ADR-0013 §Decision). --
    # Per PB-D + PB-AA: one EVT_KILL_SESSION per killed session, with
    # context="reset_admin" discriminator matching Phase 19's "context"
    # key naming for kill_my_own_sessions.
    for sid in session_ids:
        write_audit(
            conn,
            actor=os_user,
            event=EVT_KILL_SESSION,
            target=user_id,
            extra={"session_id": sid, "context": "reset_admin"},
        )

    # Per PB-U: conditional EVT_ADMIN_ENABLE_USER iff target was disabled.
    # Phase 22's admin_enable_user will be the second consumer.
    if was_disabled:
        write_audit(
            conn,
            actor=os_user,
            event=EVT_ADMIN_ENABLE_USER,
            target=user_id,
            extra={"context": "reset_admin"},
        )

    # Per PB-D + PB-BB: single summary row; sessions_killed denormalized
    # for the Phase 21 audit reader.
    write_audit(
        conn,
        actor=os_user,
        event=EVT_RESET_ADMIN,
        target=user_id,
        extra={
            "was_disabled": was_disabled,
            "sessions_killed": len(session_ids),
        },
    )

    conn.commit()

    return ResetAdminResult(
        user_id=user_id,
        sessions_killed=len(session_ids),
        was_disabled=was_disabled,
    )


# =============================================================================
# Phase 21 — Audit log reader
# =============================================================================
#
# admin_query_audit + AuditRow per ADR-0013 §amendment-2.
#
# Lives in admin.py per Phase 20 PB-Z (admin-verbs cluster). Reader is
# read-with-side-effect: every call emits one EVT_AUDIT_QUERY row at
# end-of-body per ADR-0013 §Decision ("Every privileged endpoint
# audits both its happy path and its denial path") + Phase 21 PB-16.
# =============================================================================

#: Hard cap on the ``limit`` kwarg. CLI users can pass ``--limit N`` up
#: to this value; values above are clamped silently. Protects audit-
#: reader callers from accidentally loading the entire audit table
#: into memory.
_MAX_LIMIT: int = 10_000


@dataclass(frozen=True)
class AuditRow:
    """
    A single row from the ``audit`` table, with ``extra_json``
    parsed to a Mapping.

    Phase 21 PB-9 lock. Frozen + immutable per Phase 18 :class:`User`
    + Phase 20 :class:`ResetAdminResult` precedent. ``extra`` field is
    parsed at read-time so callers do not re-parse JSON — saves a
    re-parse cost across reader-test assertions + Phase 22 audit-row
    consumers.

    The ``id`` field is exposed as part of the public API to support
    PB-10's ``after_id`` cursor pagination + the ``--json`` payload's
    ``next_after_id`` sentinel. SQLite's monotonic ``INTEGER PRIMARY
    KEY`` semantics make ``id`` stable across the audit table's
    lifetime (audit is append-only per ADR-0013 §Consequences).
    """

    #: SQLite rowid (``INTEGER PRIMARY KEY``); monotonic since audit
    #: table is append-only.
    id: int
    #: ISO-8601 with ms + Z, e.g. ``2026-05-22T03:35:59.123Z``. Phase
    #: 18 PB-35 format lock.
    ts: str
    #: ``actor_user`` column. May be NULL when the audit row represents
    #: a future system-actor event (no such event ships yet).
    actor: str | None
    #: One of :data:`mindsos_server.audit.ALL_AUDIT_EVENTS`.
    event: str
    #: ``target_user`` column. NULL when the event has no specific
    #: target user (e.g., ``EVT_AUDIT_QUERY``).
    target: str | None
    #: Parsed from the ``extra_json`` TEXT column at read time.
    extra: Mapping[str, Any]


def _normalize_iso8601(ts: str) -> str:
    """
    Normalize a lenient ISO-8601 input to the fixed-width
    ``YYYY-MM-DDTHH:MM:SS.mmmZ`` form for lexicographic SQL compare.

    Phase 21 PB-22 lock. Accepts both ``2026-05-21T00:00:00Z`` and
    ``2026-05-21T00:00:00.000Z``. Rejects date-only and Unix-timestamp
    forms (raise ``ValueError``).

    Args:
        ts: Input timestamp string.

    Returns:
        Fixed-width ISO-8601 ms+Z form. ``ts >= ?`` lex compare against
        this form matches chronological compare because the format is
        fixed-width per Phase 18 PB-35.

    Raises:
        ValueError: If ``ts`` cannot be parsed as ISO-8601 with a
            timezone, or if no timezone is present.
    """
    s = ts.strip()
    # ``datetime.fromisoformat`` doesn't natively parse trailing ``Z``
    # until Python 3.11; rewrite to ``+00:00`` for portability.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as exc:
        raise ValueError(
            f"timestamp not valid ISO-8601: {ts!r} ({exc})"
        ) from exc
    if dt.tzinfo is None:
        raise ValueError(
            f"timestamp must include timezone: {ts!r}"
        )
    dt = dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def admin_query_audit(
    conn: sqlite3.Connection,
    session: Session,
    *,
    actor: str | None = None,
    event: str | None = None,
    target: str | None = None,
    since: str | None = None,
    until: str | None = None,
    after_id: int | None = None,
    limit: int = 100,
    count_only: bool = False,
) -> list[AuditRow] | int:
    """
    Read rows from the ``audit`` table.

    Phase 21 PB-1 + PB-8 + PB-10 + PB-12 signature lock. ADR-0013
    §amendment-2 documents the conn-first positional divergence from
    the original §Decision wording + the additive ``until`` /
    ``after_id`` / ``count_only`` kwargs.

    Gated on :data:`CAN_VIEW_AUDIT_LOG` via
    :func:`mindsos_server.authz._require_or_audit` (PB-6) — emits
    :data:`mindsos_server.audit.EVT_PERMISSION_DENIED` audit row +
    raises :class:`mindsos_server.errors.PermissionDeniedError` on
    denial. Happy path emits one :data:`mindsos_server.audit.EVT_AUDIT_QUERY`
    row with a sparse filters snapshot + result count + count_only
    flag before returning (PB-16 + PB-16i + PB-17 + PB-18).

    Filter kwargs are AND'd together (PB-20). ``None`` values skip
    the WHERE clause for that column (PB-27) — does NOT match audit
    rows where the column itself is NULL.

    ``since`` / ``until`` accept lenient ISO-8601 strings (with or
    without ``.sss`` / ``Z``) per PB-22. Both bounds are inclusive
    (PB-11): SQL uses ``ts >= ?`` and ``ts <= ?``.

    ``after_id`` is a cursor for stable pagination (PB-10): SQL adds
    ``id > ?``. Combine with ``since`` AND ``until`` AND-together per
    PB-20. The cursor model + ``ORDER BY id ASC`` (PB-12) pair to
    let operators page forward in time.

    ``limit`` defaults to 100 (PB-21) and is silently clamped to
    :data:`_MAX_LIMIT` (10_000).

    ``count_only=True`` flips the SQL to ``SELECT COUNT(*)`` form
    (PB-4 reframe of "audit stats" feature) and returns the count
    as ``int``. The EVT_AUDIT_QUERY audit row is emitted identically
    with ``extra.count_only = True`` (PB-18).

    Args:
        conn: SQLite connection. Phase 21 capability-denial commits
            on this connection via ``_require_or_audit``; happy-path
            EVT_AUDIT_QUERY commit also happens here.
        session: Caller's session. ``session.has(CAN_VIEW_AUDIT_LOG)``
            is the gate; ``session.user_id`` is the audit actor.
        actor: Filter ``actor_user = ?``. None means no filter.
        event: Filter ``event = ?``. None means no filter.
        target: Filter ``target_user = ?``. None means no filter.
        since: Inclusive lower bound ``ts >= normalized(since)``.
            None means no lower bound.
        until: Inclusive upper bound ``ts <= normalized(until)``.
            None means no upper bound.
        after_id: Cursor ``id > after_id``. None means no cursor
            (start from beginning of the filtered set).
        limit: Row cap; clamped to :data:`_MAX_LIMIT`. Ignored when
            ``count_only=True``.
        count_only: If True, returns ``int`` (count of matching
            rows). If False, returns ``list[AuditRow]``.

    Returns:
        ``list[AuditRow]`` in ``id`` ASC order when ``count_only=False``
        (default). ``int`` when ``count_only=True``.

    Raises:
        PermissionDeniedError: If ``session`` lacks ``CAN_VIEW_AUDIT_LOG``.
            The EVT_PERMISSION_DENIED audit row is written + committed
            BEFORE the raise (see ``_require_or_audit``).
        ValueError: If ``since`` / ``until`` cannot be parsed as
            ISO-8601 with timezone (see ``_normalize_iso8601``).
    """
    # 1. Capability gate (PB-6 + PB-13). Writes EVT_PERMISSION_DENIED
    #    + commits + raises on denial. Happy path returns silently;
    #    the verb's own happy-path audit (EVT_AUDIT_QUERY) fires
    #    later in this body per PB-16.
    _require_or_audit(
        conn, session, CAN_VIEW_AUDIT_LOG, verb="admin_query_audit",
    )

    # 2. Build WHERE clauses + params from non-None filters (PB-27
    #    sparse-filter semantic). Order matches sparse-filter snapshot
    #    insertion below so reviewers can pair the SQL with the audit
    #    row's extra_json.filters payload.
    where_clauses: list[str] = []
    params: list[Any] = []
    if actor is not None:
        where_clauses.append("actor_user = ?")
        params.append(actor)
    if event is not None:
        where_clauses.append("event = ?")
        params.append(event)
    if target is not None:
        where_clauses.append("target_user = ?")
        params.append(target)
    if since is not None:
        where_clauses.append("ts >= ?")
        params.append(_normalize_iso8601(since))
    if until is not None:
        where_clauses.append("ts <= ?")
        params.append(_normalize_iso8601(until))
    if after_id is not None:
        where_clauses.append("id > ?")
        params.append(after_id)

    where_sql = (
        "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    )

    # 3. Execute the read query. ASC + LIMIT per PB-10 + PB-12 + PB-21.
    rows_returned: list[AuditRow] | int
    if count_only:
        sql = f"SELECT COUNT(*) FROM audit {where_sql}".rstrip()
        row = conn.execute(sql, params).fetchone()
        count = int(row[0])
        rows_returned = count
    else:
        effective_limit = min(int(limit), _MAX_LIMIT)
        sql = (
            f"SELECT id, ts, actor_user, event, target_user, extra_json "
            f"FROM audit {where_sql} ORDER BY id ASC LIMIT ?"
        )
        result = conn.execute(sql, params + [effective_limit]).fetchall()
        rows = [
            AuditRow(
                id=int(r[0]),
                ts=r[1],
                actor=r[2],
                event=r[3],
                target=r[4],
                extra=json.loads(r[5]) if r[5] else {},
            )
            for r in result
        ]
        rows_returned = rows
        count = len(rows)

    # 4. Happy-path audit emission (PB-16 + PB-16i + PB-17 + PB-18).
    #    Sparse filters snapshot: only non-None kwargs are recorded.
    #    ``limit`` is always recorded (even at default 100) so
    #    reviewers can reconstruct the exact query that was issued.
    filters_snapshot: dict[str, Any] = {}
    if actor is not None:
        filters_snapshot["actor"] = actor
    if event is not None:
        filters_snapshot["event"] = event
    if target is not None:
        filters_snapshot["target"] = target
    if since is not None:
        filters_snapshot["since"] = since
    if until is not None:
        filters_snapshot["until"] = until
    if after_id is not None:
        filters_snapshot["after_id"] = after_id
    filters_snapshot["limit"] = int(limit)

    write_audit(
        conn,
        actor=session.user_id,
        event=EVT_AUDIT_QUERY,
        target=None,
        extra={
            "filters": filters_snapshot,
            "count": count,
            "count_only": count_only,
        },
    )
    conn.commit()

    return rows_returned


# =============================================================================
# Phase 22 — Admin user-management ops (R1–R5; 27 locked picks)
# =============================================================================
#
# Six verbs (R1 PB-2 admin subgroup): admin_promote_user, admin_demote_user,
# admin_disable_user, admin_enable_user, admin_kill_session, hard_delete_user.
# Plus shared helpers: _assert_not_sole_admin (PB-7) + admin_tx (PB-24
# BEGIN IMMEDIATE wrapper closing the WAL concurrent-admin race).
#
# All six verbs gate via _require_or_audit (Phase 21 PB-6 wrapper) before
# entering the tx; happy-path audit emission is verb-specific per R2 PB-16
# (each verb writes its own EVT_ADMIN_*_USER / EVT_KILL_SESSION / EVT_HARD_DELETE_USER
# audit rows inside the tx). Per-row EVT_KILL_SESSION precedes the summary
# audit row in ASC id order so audit-log readers see "what happened, then
# the conclusion" (R3 non-pushback lock).
#
# Capability gating (ADR-0002):
# * CAN_MANAGE_USERS → promote / demote / disable / enable.
# * CAN_KILL_SESSION → admin_kill_session.
# * CAN_HARD_DELETE_ARCHIVED → hard_delete_user (cap name is documentary
#   debt per R2 PB-17 — no archive-first precondition).
#
# Cross-user read (ADR-0008): DEFERRED to Phase 25 per R1 PB-1 +
# ADR-0008 §amendment-1; lands alongside MindsOSServer + LocalPersister
# (ADR-0011 §amendment-1). Not in Phase 22 scope.
#
# See ``confirmation_docs/PHASE_22_DESIGN_LOG.md`` for the 27-pick ledger
# across 5 design rounds + ADR-0012 §amendment-3 + ADR-0008 §amendment-1.
# =============================================================================


# ---------------------------------------------------------------------------
# admin_tx — BEGIN IMMEDIATE wrapper (R4 PB-24)
# ---------------------------------------------------------------------------


@contextmanager
def admin_tx(conn: sqlite3.Connection) -> Iterator[None]:
    """
    Wrap an admin-verb body in a BEGIN IMMEDIATE transaction.

    Phase 22 R4 PB-24 lock. SQLite WAL mode (Phase 18 PB-19) gives each
    DEFERRED transaction a snapshot-at-tx-start view. Two concurrent
    admin verbs in separate connections can both read the pre-state,
    both pass :func:`_assert_not_sole_admin`, then both commit — leaving
    the system with zero active admins. ``BEGIN IMMEDIATE`` acquires
    the RESERVED write-lock at tx start; the second concurrent verb
    blocks (up to ``busy_timeout = 5000`` ms set in
    :func:`mindsos_server._db.open_db`), and when it resumes its
    snapshot reflects the first verb's commit.

    Pattern:

    .. code-block:: python

        def admin_demote_user(conn, session, *, target_user_id):
            _require_or_audit(conn, session, CAN_MANAGE_USERS,
                              verb="admin_demote_user")
            with admin_tx(conn):
                # all reads + checks + mutations + audit writes
                ...

    Note: ``_require_or_audit`` on the DENIAL path writes
    EVT_PERMISSION_DENIED + commits + raises BEFORE the verb enters
    ``admin_tx``. On the HAPPY path it returns silently with no DB
    activity, so ``BEGIN IMMEDIATE`` succeeds (no auto-BEGIN has fired
    yet under Python sqlite3's DEFERRED isolation level).

    Reset-admin (Phase 20) does NOT use this wrapper — flagged as a
    known minor inconsistency for future cleanup (reset-admin has no
    ``_assert_not_sole_admin`` consumer; the cross-process race wasn't
    surfaced at Phase 20).

    Args:
        conn: SQLite connection from
            :func:`mindsos_server._db.open_db` (DEFERRED isolation +
            WAL + busy_timeout=5000 per Phase 18 PB-19).

    Yields:
        ``None``. The caller does NOT manually ``commit()`` /
        ``rollback()`` — this context manager owns those boundaries.

    Raises:
        Any exception raised inside the ``with`` block triggers
        ``conn.rollback()`` then re-raises.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()


# ---------------------------------------------------------------------------
# _assert_not_sole_admin — sole-admin invariant helper (R1 PB-7)
# ---------------------------------------------------------------------------


def _assert_not_sole_admin(
    conn: sqlite3.Connection, target_user_id: str
) -> None:
    """
    Raise :class:`LastAdminError` if removing/demoting ``target_user_id``
    would leave the system with zero active admins.

    Phase 22 R1 PB-7 lock. ADR-0012 §Decision: "The following admin
    endpoints refuse to leave the system with zero admins... Enforcement
    is a single helper ``_assert_not_sole_admin(target_user_id)`` that
    counts ``role='admin' AND disabled=0`` rows."

    Implementation: single SELECT returns the list of active-admin
    user_ids; the invariant fires iff the list is exactly
    ``[target_user_id]`` (R3 non-pushback lock — atomic-in-tx, one
    query, most readable).

    Called by :func:`admin_demote_user`, :func:`admin_disable_user`,
    and :func:`hard_delete_user` — the three callers ADR-0012
    §Decision enumerates. Promote / enable / kill-session do NOT call
    this helper (they cannot shrink the active-admin count).

    Args:
        conn: SQLite connection inside an :func:`admin_tx` transaction.
        target_user_id: The user the caller is about to
            demote/disable/delete. The check is "is THIS user the only
            active admin?" — not "are there ANY active admins?"

    Raises:
        LastAdminError: If the active-admin set is exactly
            ``{target_user_id}``.
    """
    rows = conn.execute(
        "SELECT user_id FROM users WHERE actor_role = 'admin' AND disabled = 0"
    ).fetchall()
    active_admins = [r[0] for r in rows]
    if active_admins == [target_user_id]:
        raise LastAdminError(target_user_id)


# ---------------------------------------------------------------------------
# Result dataclasses (R3 PB-19) — one per verb, frozen, per-verb fields
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PromoteUserResult:
    """
    Return type of :func:`admin_promote_user`.

    Phase 22 R3 PB-19 lock. ``prior_role`` is always ``"user"`` (the
    verb refuses already-admin targets via :class:`AlreadyAnAdminError`
    per R1 PB-3); recorded for symmetry with :class:`DemoteUserResult`
    and audit-row :data:`EVT_ADMIN_PROMOTE_USER` extra_json shape.
    """

    target_user_id: str
    prior_role: Literal["user"]
    ts: str


@dataclass(frozen=True)
class DemoteUserResult:
    """
    Return type of :func:`admin_demote_user`.

    Phase 22 R3 PB-19 lock. ``sessions_killed`` denormalized per R2 PB-16
    (also appears in :data:`EVT_ADMIN_DEMOTE_USER` extra_json — saves
    a future audit-reader from joining EVT_KILL_SESSION rows).
    """

    target_user_id: str
    prior_role: Literal["admin"]
    sessions_killed: int
    ts: str


@dataclass(frozen=True)
class DisableUserResult:
    """
    Return type of :func:`admin_disable_user`.

    Phase 22 R3 PB-19 lock. ``was_already_disabled`` records the no-op
    marker for idempotent invocations (R2 PB-15 audit-always semantic);
    ``sessions_killed`` denormalized per R2 PB-16.
    """

    target_user_id: str
    was_already_disabled: bool
    sessions_killed: int
    ts: str


@dataclass(frozen=True)
class EnableUserResult:
    """
    Return type of :func:`admin_enable_user`.

    Phase 22 R3 PB-19 lock. ``was_already_enabled`` records the no-op
    marker; the verb emits EVT_ADMIN_ENABLE_USER on every invocation
    per R1 PB-10 (audit-always-on-privileged-endpoint-call per ADR-0013
    §Decision).
    """

    target_user_id: str
    was_already_enabled: bool
    ts: str


@dataclass(frozen=True)
class KillSessionResult:
    """
    Return type of :func:`admin_kill_session`.

    Phase 22 R3 PB-19 lock. ``target_user_id`` is the session's owner
    (looked up from the sessions table before delete); useful for CLI
    confirmation output + future audit-reader correlation.
    """

    target_session_id: str
    target_user_id: str
    ts: str


@dataclass(frozen=True)
class HardDeleteUserResult:
    """
    Return type of :func:`hard_delete_user`.

    Phase 22 R3 PB-19 lock. ``prior_role`` + ``was_disabled`` +
    ``sessions_killed`` denormalized per R2 PB-16 so the audit reader
    can reconstruct the deleted user's state at delete time without
    needing the user row (which is gone — CASCADE deleted on user
    DELETE per Phase 18 schema FK).
    """

    target_user_id: str
    prior_role: Literal["user", "admin"]
    was_disabled: bool
    sessions_killed: int
    ts: str


# ---------------------------------------------------------------------------
# admin_promote_user (R1 PB-3 + R1 PB-5 + R2 PB-12)
# ---------------------------------------------------------------------------


def admin_promote_user(
    conn: sqlite3.Connection,
    session: Session,
    *,
    target_user_id: str,
) -> PromoteUserResult:
    """
    Promote a non-admin user to ``actor_role='admin'``.

    Phase 22 R1 PB-3 + R1 PB-5 + R2 PB-12 locks. Gated on
    :data:`CAN_MANAGE_USERS` via :func:`_require_or_audit` (Phase 21
    PB-6 wrapper); session-immutable per ADR-0002 — live sessions of
    the promoted user keep their old capabilities until lazy expiry /
    re-login (per R1 PB-5: silent promote, no session-kill side
    effect).

    Pre-conditions (R1 PB-8 check-first ordering):

    1. Caller has ``CAN_MANAGE_USERS`` (else :class:`PermissionDeniedError`
       per Phase 21 PB-6 + PB-13).
    2. Target ``user_id`` exists in ``users`` (else
       :class:`UserNotFoundError` per Phase 20 PB-O reuse).
    3. Target ``actor_role != 'admin'`` (else
       :class:`AlreadyAnAdminError` per R1 PB-3 — re-promote is NOT
       idempotent; explicit rejection prevents masking accidental
       double-promotes).

    Per R2 PB-12: target's ``disabled`` flag is LEFT UNCHANGED.
    Promoting a disabled user gives a "disabled admin"; the caller
    can chain ``admin enable-user X && admin promote-user X`` if both
    are intended. No auto-enable side effect (diverges from
    reset-admin's recovery-verb auto-enable for explicit reasons:
    promote is a management verb, not a recovery verb).

    Audit emitted: 1× :data:`EVT_ADMIN_PROMOTE_USER` with
    ``extra = {"prior_role": "user"}`` per R2 PB-16.

    No session-kill: per R1 PB-5, promotion expands caps; existing
    sessions with USER_CAPS are safe to keep until they expire or
    re-login. ADR-0002 §Rationale "Session is immutable after issue;
    permissions can't drift mid-request" governs.

    Args:
        conn: SQLite connection (DEFERRED isolation; see :func:`admin_tx`).
        session: Caller's session; ``session.user_id`` becomes audit
            ``actor_user``.
        target_user_id: User to promote.

    Returns:
        :class:`PromoteUserResult` with ``target_user_id``, ``prior_role``
        (always ``"user"``), and ``ts``.

    Raises:
        PermissionDeniedError: Caller lacks ``CAN_MANAGE_USERS``.
        UserNotFoundError: Target does not exist.
        AlreadyAnAdminError: Target is already an admin.
    """
    _require_or_audit(
        conn, session, CAN_MANAGE_USERS, verb="admin_promote_user",
    )
    with admin_tx(conn):
        row = conn.execute(
            "SELECT actor_role FROM users WHERE user_id = ?",
            (target_user_id,),
        ).fetchone()
        if row is None:
            raise UserNotFoundError(target_user_id)
        actor_role = row[0]
        if actor_role == "admin":
            raise AlreadyAnAdminError(target_user_id)

        conn.execute(
            "UPDATE users SET actor_role = 'admin' WHERE user_id = ?",
            (target_user_id,),
        )
        write_audit(
            conn,
            actor=session.user_id,
            event=EVT_ADMIN_PROMOTE_USER,
            target=target_user_id,
            extra={"prior_role": "user"},
        )

    return PromoteUserResult(
        target_user_id=target_user_id,
        prior_role="user",
        ts=_now_utc_iso(),
    )


# ---------------------------------------------------------------------------
# admin_demote_user (R1 PB-4 + PB-7 + PB-8 + R2 PB-14 + R4 PB-25)
# ---------------------------------------------------------------------------


def admin_demote_user(
    conn: sqlite3.Connection,
    session: Session,
    *,
    target_user_id: str,
) -> DemoteUserResult:
    """
    Demote an admin to ``actor_role='user'``; kill all their sessions.

    Phase 22 R1 PB-4 + PB-7 + PB-8 locks. Per R1 PB-4 + ADR-0002
    §Rationale: session-immutable caps mean a live admin session
    keeps ``ADMIN_CAPS`` until expiry — so demote MUST kill all of
    target's sessions atomically to make the demote observable.

    Pre-conditions (R1 PB-8 check-first ordering, inside :func:`admin_tx`
    per R4 PB-24 concurrent-admin race protection):

    1. Caller has ``CAN_MANAGE_USERS`` (PermissionDeniedError on
       denial).
    2. Target exists (UserNotFoundError on missing).
    3. Target is an admin (NotAnAdminError on non-admin; per R4 PB-25
       the verb-agnostic message is just ``"user X has actor_role=Y;
       admin role required"`` — CLI handlers inject "cannot demote
       non-admin" framing on stderr).
    4. Target is NOT the sole active admin (LastAdminError via
       :func:`_assert_not_sole_admin`).

    State mutations (single tx, state-then-audit per Phase 20 PB-R
    precedent):

    * Capture session_ids (SELECT BEFORE delete).
    * ``DELETE FROM sessions WHERE user_id=?``.
    * ``UPDATE users SET actor_role='user' WHERE user_id=?``.
    * N× :data:`EVT_KILL_SESSION` per killed session with
      ``extra = {"session_id": sid, "context": "admin_demote_user"}``
      (R2 PB-14 vocab).
    * 1× :data:`EVT_ADMIN_DEMOTE_USER` summary with ``extra =
      {"prior_role": "admin", "sessions_killed": N}`` (R2 PB-16).

    Self-demote allowed per R2 PB-18 — if calling admin demotes
    themselves, ``_assert_not_sole_admin`` enforces "another admin
    exists"; on success their own session is killed and they're
    locked out until re-login as a regular user (or `reset-admin`
    via filesystem if they were the sole admin and crashed past the
    helper, which can't happen by construction).

    Raises:
        PermissionDeniedError, UserNotFoundError, NotAnAdminError,
        LastAdminError.
    """
    _require_or_audit(
        conn, session, CAN_MANAGE_USERS, verb="admin_demote_user",
    )
    with admin_tx(conn):
        row = conn.execute(
            "SELECT actor_role FROM users WHERE user_id = ?",
            (target_user_id,),
        ).fetchone()
        if row is None:
            raise UserNotFoundError(target_user_id)
        actor_role = row[0]
        if actor_role != "admin":
            raise NotAnAdminError(target_user_id, actor_role)

        _assert_not_sole_admin(conn, target_user_id)

        session_ids = [
            r[0]
            for r in conn.execute(
                "SELECT session_id FROM sessions WHERE user_id = ?",
                (target_user_id,),
            ).fetchall()
        ]

        conn.execute(
            "DELETE FROM sessions WHERE user_id = ?",
            (target_user_id,),
        )
        conn.execute(
            "UPDATE users SET actor_role = 'user' WHERE user_id = ?",
            (target_user_id,),
        )

        for sid in session_ids:
            write_audit(
                conn,
                actor=session.user_id,
                event=EVT_KILL_SESSION,
                target=target_user_id,
                extra={"session_id": sid, "context": "admin_demote_user"},
            )
        write_audit(
            conn,
            actor=session.user_id,
            event=EVT_ADMIN_DEMOTE_USER,
            target=target_user_id,
            extra={
                "prior_role": "admin",
                "sessions_killed": len(session_ids),
            },
        )

    return DemoteUserResult(
        target_user_id=target_user_id,
        prior_role="admin",
        sessions_killed=len(session_ids),
        ts=_now_utc_iso(),
    )


# ---------------------------------------------------------------------------
# admin_disable_user (R1 PB-6 + PB-7 + R2 PB-14 + PB-15 + R2 PB-18)
# ---------------------------------------------------------------------------


def admin_disable_user(
    conn: sqlite3.Connection,
    session: Session,
    *,
    target_user_id: str,
) -> DisableUserResult:
    """
    Set ``users.disabled=1`` on a user; kill all their sessions.

    Phase 22 R1 PB-6 + PB-7 + R2 PB-15 + PB-18 locks. Same
    session-immutability argument as :func:`admin_demote_user`:
    disabling a user must kill their sessions atomically so the
    disable is observable, not just queued for next-login.

    Pre-conditions (check-first; R4 PB-24 admin_tx):

    1. Caller has ``CAN_MANAGE_USERS``.
    2. Target exists.
    3. If target is an ACTIVE admin (``actor_role='admin' AND
       disabled=0``), check sole-admin invariant. Disabling an
       already-disabled admin doesn't shrink the active-admin count
       — skip the check (idempotency per R2 PB-15).

    Per R2 PB-15: idempotent on already-disabled — emit
    :data:`EVT_ADMIN_DISABLE_USER` with ``extra.was_already_disabled
    = True`` and ``sessions_killed = N`` (still kills any extant
    sessions, though typically zero for an already-disabled user).
    The audit row records the verb invocation; ``extra`` records the
    no-op marker.

    Audit emitted (state-then-audit):

    * N× :data:`EVT_KILL_SESSION` (``context = "admin_disable_user"``
      per R2 PB-14).
    * 1× :data:`EVT_ADMIN_DISABLE_USER` with ``extra =
      {"was_already_disabled": bool, "sessions_killed": N}`` per R2 PB-16.

    Raises:
        PermissionDeniedError, UserNotFoundError, LastAdminError.
    """
    _require_or_audit(
        conn, session, CAN_MANAGE_USERS, verb="admin_disable_user",
    )
    with admin_tx(conn):
        row = conn.execute(
            "SELECT actor_role, disabled FROM users WHERE user_id = ?",
            (target_user_id,),
        ).fetchone()
        if row is None:
            raise UserNotFoundError(target_user_id)
        actor_role, disabled_int = row[0], int(row[1])
        was_already_disabled = bool(disabled_int)

        # Only check sole-admin invariant if disabling will actually shrink
        # the active-admin count (target is currently an ACTIVE admin).
        if actor_role == "admin" and not was_already_disabled:
            _assert_not_sole_admin(conn, target_user_id)

        session_ids = [
            r[0]
            for r in conn.execute(
                "SELECT session_id FROM sessions WHERE user_id = ?",
                (target_user_id,),
            ).fetchall()
        ]

        conn.execute(
            "DELETE FROM sessions WHERE user_id = ?",
            (target_user_id,),
        )
        conn.execute(
            "UPDATE users SET disabled = 1 WHERE user_id = ?",
            (target_user_id,),
        )

        for sid in session_ids:
            write_audit(
                conn,
                actor=session.user_id,
                event=EVT_KILL_SESSION,
                target=target_user_id,
                extra={
                    "session_id": sid,
                    "context": "admin_disable_user",
                },
            )
        write_audit(
            conn,
            actor=session.user_id,
            event=EVT_ADMIN_DISABLE_USER,
            target=target_user_id,
            extra={
                "was_already_disabled": was_already_disabled,
                "sessions_killed": len(session_ids),
            },
        )

    return DisableUserResult(
        target_user_id=target_user_id,
        was_already_disabled=was_already_disabled,
        sessions_killed=len(session_ids),
        ts=_now_utc_iso(),
    )


# ---------------------------------------------------------------------------
# admin_enable_user (R1 PB-10 + R2 PB-15 + R2 PB-18)
# ---------------------------------------------------------------------------


def admin_enable_user(
    conn: sqlite3.Connection,
    session: Session,
    *,
    target_user_id: str,
) -> EnableUserResult:
    """
    Set ``users.disabled=0`` on a user.

    Phase 22 R1 PB-10 + R2 PB-15 locks. Thin verb: UPDATE + audit
    always; idempotent on already-enabled (``was_already_enabled =
    True`` recorded in result + audit extra). Diverges from Phase 20
    reset-admin's PB-U conditional emission pattern: P20's
    conditional was inside reset-admin (a recovery verb); P22's
    enable-user is a standalone management verb, and ADR-0013
    §Decision "every privileged endpoint audits both happy + denial"
    targets standalone verb invocations.

    Pre-conditions:

    1. Caller has ``CAN_MANAGE_USERS``.
    2. Target exists (UserNotFoundError).

    No sole-admin check (enabling cannot shrink the active-admin count).
    No session-kill (enabling is the safer direction; symmetric inverse
    of disable but no destructive side effects).

    Audit emitted: 1× :data:`EVT_ADMIN_ENABLE_USER` with ``extra =
    {"was_already_enabled": bool}`` per R2 PB-16. The Phase 20
    EVT_ADMIN_ENABLE_USER extra was ``{"context": "reset_admin"}`` —
    the two extra shapes coexist by event-source discriminator
    (P20 rows have ``context``, P22 rows have ``was_already_enabled``;
    future audit readers can branch on key presence).

    Raises:
        PermissionDeniedError, UserNotFoundError.
    """
    _require_or_audit(
        conn, session, CAN_MANAGE_USERS, verb="admin_enable_user",
    )
    with admin_tx(conn):
        row = conn.execute(
            "SELECT disabled FROM users WHERE user_id = ?",
            (target_user_id,),
        ).fetchone()
        if row is None:
            raise UserNotFoundError(target_user_id)
        was_already_enabled = not bool(int(row[0]))

        conn.execute(
            "UPDATE users SET disabled = 0 WHERE user_id = ?",
            (target_user_id,),
        )
        write_audit(
            conn,
            actor=session.user_id,
            event=EVT_ADMIN_ENABLE_USER,
            target=target_user_id,
            extra={"was_already_enabled": was_already_enabled},
        )

    return EnableUserResult(
        target_user_id=target_user_id,
        was_already_enabled=was_already_enabled,
        ts=_now_utc_iso(),
    )


# ---------------------------------------------------------------------------
# admin_kill_session (R1 PB-9 + R2 PB-13 + PB-14)
# ---------------------------------------------------------------------------


def admin_kill_session(
    conn: sqlite3.Connection,
    session: Session,
    *,
    target_session_id: str,
) -> KillSessionResult:
    """
    Delete a specific session row by ``session_id``.

    Phase 22 R1 PB-9 + R2 PB-13 + PB-14 locks. Deliberate-target verb:
    arg shape is ``target_session_id`` (NOT user_id) per R1 PB-9. The
    "kill all sessions for user X" semantic is already covered by
    Phase 19 ``kill_my_own_sessions`` + Phase 20 reset-admin +
    Phase 22 ``admin_disable_user`` / ``admin_demote_user``.

    Pre-conditions (check-first; admin_tx):

    1. Caller has ``CAN_KILL_SESSION``.
    2. Target session_id exists (else :class:`SessionNotFoundError`
       per R2 PB-13 — idempotency would hide operator typos on
       session_ids).

    Order (state-then-audit per Phase 20 PB-R precedent):

    1. SELECT ``user_id`` from the sessions row (needed for
       audit ``target_user``).
    2. DELETE the session row.
    3. Write 1× :data:`EVT_KILL_SESSION` with ``extra = {"session_id":
       sid, "context": "admin_kill_session"}`` per R2 PB-14.

    Self-target allowed per R2 PB-18 — admin killing their own
    session is permitted (they re-login afterward). No special-case
    guard (filesystem authority is the recovery floor per ADR-0012
    §Rationale).

    Args:
        target_session_id: The ``sessions.session_id`` to delete.

    Returns:
        :class:`KillSessionResult` with ``target_session_id``,
        ``target_user_id`` (session owner), and ``ts``.

    Raises:
        PermissionDeniedError, SessionNotFoundError.
    """
    _require_or_audit(
        conn, session, CAN_KILL_SESSION, verb="admin_kill_session",
    )
    with admin_tx(conn):
        row = conn.execute(
            "SELECT user_id FROM sessions WHERE session_id = ?",
            (target_session_id,),
        ).fetchone()
        if row is None:
            raise SessionNotFoundError(target_session_id)
        target_user_id = row[0]

        conn.execute(
            "DELETE FROM sessions WHERE session_id = ?",
            (target_session_id,),
        )
        write_audit(
            conn,
            actor=session.user_id,
            event=EVT_KILL_SESSION,
            target=target_user_id,
            extra={
                "session_id": target_session_id,
                "context": "admin_kill_session",
            },
        )

    return KillSessionResult(
        target_session_id=target_session_id,
        target_user_id=target_user_id,
        ts=_now_utc_iso(),
    )


# ---------------------------------------------------------------------------
# hard_delete_user (R1 PB-11 + R2 PB-14 + PB-17 + PB-18)
# ---------------------------------------------------------------------------


def hard_delete_user(
    conn: sqlite3.Connection,
    session: Session,
    *,
    target_user_id: str,
) -> HardDeleteUserResult:
    """
    Permanently delete a user row; FK CASCADE removes their sessions.

    Phase 22 R1 PB-11 + R2 PB-17 + PB-18 locks. The audit table has
    NO foreign key to ``users`` (per Phase 18 ``_schema.py`` lock) —
    audit rows about a hard-deleted user OUTLIVE the user row, per
    ADR-0013 §Consequences "audit MUST outlive subjects."

    The cap name :data:`CAN_HARD_DELETE_ARCHIVED` is documentary debt
    per R2 PB-17 — there's no archive step (no ``users.archived``
    column); rename deferred per ADR-0002 §Consequences ("Capability
    strings are now part of the stable API surface; renaming them is
    a breaking change.").

    Pre-conditions (check-first; admin_tx):

    1. Caller has ``CAN_HARD_DELETE_ARCHIVED``.
    2. Target exists (UserNotFoundError).
    3. If target is an ACTIVE admin, check sole-admin invariant. A
       disabled admin doesn't count toward "active admins" — deleting
       them never triggers LastAdminError. Self-delete of the last
       active admin IS allowed if there's another admin (the helper
       gates on count, not on self/other identity).

    Order (audit-then-state per R1 PB-11 — capture session_ids before
    CASCADE wipes them):

    1. SELECT actor_role + disabled (for audit extra + sole-admin check).
    2. _assert_not_sole_admin (conditional on active-admin target).
    3. SELECT session_ids (for per-session audit emission).
    4. Emit N× :data:`EVT_KILL_SESSION` (``context = "hard_delete_user"``
       per R2 PB-14) — written BEFORE the DELETE because CASCADE
       would otherwise clear sessions before we know their ids.
    5. Emit 1× :data:`EVT_HARD_DELETE_USER` summary with ``extra =
       {"prior_role": str, "was_disabled": bool, "sessions_killed": N}``
       per R2 PB-16.
    6. ``DELETE FROM users WHERE user_id=?`` — CASCADE auto-deletes
       sessions rows.

    All audit rows have ``target_user = target_user_id`` (string, no
    FK); they persist after the DELETE.

    Raises:
        PermissionDeniedError, UserNotFoundError, LastAdminError.
    """
    _require_or_audit(
        conn, session, CAN_HARD_DELETE_ARCHIVED, verb="hard_delete_user",
    )
    with admin_tx(conn):
        row = conn.execute(
            "SELECT actor_role, disabled FROM users WHERE user_id = ?",
            (target_user_id,),
        ).fetchone()
        if row is None:
            raise UserNotFoundError(target_user_id)
        actor_role, disabled_int = row[0], int(row[1])
        was_disabled = bool(disabled_int)

        # Only check sole-admin if target is an ACTIVE admin (deleting a
        # disabled admin doesn't shrink the active-admin count).
        if actor_role == "admin" and not was_disabled:
            _assert_not_sole_admin(conn, target_user_id)

        session_ids = [
            r[0]
            for r in conn.execute(
                "SELECT session_id FROM sessions WHERE user_id = ?",
                (target_user_id,),
            ).fetchall()
        ]

        # Audit BEFORE DELETE — CASCADE clears sessions; audit table has
        # no FK so target_user_id string survives the user-row delete.
        for sid in session_ids:
            write_audit(
                conn,
                actor=session.user_id,
                event=EVT_KILL_SESSION,
                target=target_user_id,
                extra={
                    "session_id": sid,
                    "context": "hard_delete_user",
                },
            )
        write_audit(
            conn,
            actor=session.user_id,
            event=EVT_HARD_DELETE_USER,
            target=target_user_id,
            extra={
                "prior_role": actor_role,
                "was_disabled": was_disabled,
                "sessions_killed": len(session_ids),
            },
        )

        conn.execute(
            "DELETE FROM users WHERE user_id = ?",
            (target_user_id,),
        )

    return HardDeleteUserResult(
        target_user_id=target_user_id,
        prior_role=actor_role,
        was_disabled=was_disabled,
        sessions_killed=len(session_ids),
        ts=_now_utc_iso(),
    )
