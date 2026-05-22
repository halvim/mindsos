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

from mindsos_server._argon2 import (
    PRODUCTION_PARAMS,
    Argon2Params,
    hash_password,
)
from mindsos_server.audit import (
    EVT_ADMIN_ENABLE_USER,
    EVT_AUDIT_QUERY,
    EVT_KILL_SESSION,
    EVT_RESET_ADMIN,
    write_audit,
)
from mindsos_server.authz import _require_or_audit
from mindsos_server.capabilities import CAN_VIEW_AUDIT_LOG
from mindsos_server.errors import NotAnAdminError, UserNotFoundError
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
