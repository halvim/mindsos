"""
User store CRUD + verify for the Server Layer.

Phase 18 surface (per row Features + design log §5); Phase 19 amends
:func:`verify` per PB-9 / ADR-0013 §amendment-1 to drop the internal
audit write (callers — :func:`mindsos_server.sessions.login` +
:func:`mindsos_server.sessions.kill_my_own_sessions` — own the
``EVT_LOGIN_FAILED`` audit emission):

* :class:`User` — frozen dataclass view of a ``users`` row (no
  ``password_hash`` field per Phase 18 PB-24; never returned to callers).
* :func:`insert_user` — argon2id-hash + INSERT; raises
  :class:`UserAlreadyExistsError` on UNIQUE conflict per PB-30; enforces
  ``user_id`` charset per PB-7 (imports ``_USER_ID_RE`` from KL
  identifiers).
* :func:`list_users` — SELECT all users; returns ``list[User]`` sorted
  by ``user_id``.
* :func:`verify` — argon2id verify + ``disabled`` honoring per PB-15;
  raises :class:`AuthFailedError` (single class, private cause) per
  PB-23 on any failure; closes timing leak per PB-22 by running argon2
  against :data:`_SENTINEL_HASH` on user-not-found. **Phase 19 PB-9
  revision: pure predicate; no audit write.**
* :func:`_insert_first_admin` — bootstrap helper per PB-9; pure insert
  with ``actor_role='admin'``; idempotency at CLI caller per PB-29.

Cross-references:

* ADR-0044 §amendment-1 — ``user_id`` charset regex (imported from KL).
* ADR-0003 — argon2id; Phase 18 PB-14 explicit params at every call.
* ADR-0013 — audit writer + ``EVT_ADMIN_CREATE_USER`` consumed here;
  ``EVT_LOGIN_FAILED`` is NOT emitted by this module at Phase 19+ per
  §amendment-1 (callers own it).
* Phase 18 PB-7 — ``_USER_ID_RE`` imported from
  ``mindsos_knowledge.identifiers`` (ADR-0010 permits server→KL
  direction; only KL→server is forbidden).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

# Phase 18 PB-7 — server imports KL's regex (ADR-0010 permits this
# direction). Single source of truth for the charset constraint locked
# at Phase 12 PB-11 / ADR-0044 §amendment-1.
from mindsos_knowledge.identifiers import _USER_ID_RE

from mindsos_server._argon2 import (
    Argon2Params,
    hash_password,
    verify_against_sentinel,
    verify_password,
)
from mindsos_server.audit import (
    EVT_ADMIN_CREATE_USER,
    _now_utc_iso,
    write_audit,
)
from mindsos_server.errors import (
    AuthFailedError,
    AuthFailureCause,
    UserAlreadyExistsError,
)


@dataclass(frozen=True, slots=True)
class User:
    """
    Immutable view of a ``users`` row.

    Per Phase 18 PB-24: NO ``password_hash`` field — the hash is never
    returned to callers. Internal code that needs the hash (only
    :func:`verify` at Phase 18) queries it directly from SQLite and
    discards immediately.

    Fields match the user-facing columns of the ``users`` table:

    * ``user_id`` — charset-constrained per ADR-0044 §am1.
    * ``actor_role`` — ``"user"`` | ``"admin"``.
    * ``disabled`` — bool; True iff ``users.disabled = 1``. Verify
      honors per Phase 18 PB-15.
    * ``created_at`` — :class:`datetime` parsed from the TEXT ISO-8601
      UTC ms column per Phase 18 PB-35.
    """

    user_id: str
    actor_role: Literal["user", "admin"]
    disabled: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# User-id charset validation
# ---------------------------------------------------------------------------


def _validate_user_id(user_id: str) -> None:
    """
    Validate ``user_id`` against the regex inherited from KL per Phase 18
    PB-7 / ADR-0044 §amendment-1.

    Raises :class:`ValueError` on mismatch. The exception is allowed to
    propagate raw because charset violations are caller programming
    errors (CLI / future HTTP layer should reject before reaching here);
    not authentication failures.
    """
    if not isinstance(user_id, str) or not _USER_ID_RE.match(user_id):
        raise ValueError(
            f"user_id must match {_USER_ID_RE.pattern!r}; got {user_id!r}"
        )


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


def insert_user(
    conn: sqlite3.Connection,
    user_id: str,
    password: str,
    *,
    actor_role: Literal["user", "admin"] = "user",
    params: Argon2Params,
    audit_actor: str | None = None,
) -> User:
    """
    Insert a new user.

    Hashes the password with argon2id at the given ``params`` (Phase 18
    PB-14 — no default; caller is explicit), inserts the row, writes an
    ``EVT_ADMIN_CREATE_USER`` audit row in the same transaction per
    ADR-0013 §Decision, and returns a :class:`User` view.

    Args:
        conn: SQLite connection from
            :func:`mindsos_server._db.open_db`.
        user_id: Charset-constrained per ADR-0044 §am1.
        password: Plaintext; hashed before insert.
        actor_role: Default ``"user"``. Bootstrap helper passes ``"admin"``.
        params: argon2id parameters (``PRODUCTION_PARAMS`` in production;
            ``_TEST_FAST_PARAMS`` in tests).
        audit_actor: ``user_id`` of the actor performing the create. None
            when no Session exists (e.g., bootstrap path uses the OS
            user — see :func:`_insert_first_admin`).

    Raises:
        ValueError: ``user_id`` fails the regex per PB-7.
        UserAlreadyExistsError: ``user_id`` already exists per PB-30.

    Returns:
        :class:`User` view of the newly-inserted row.
    """
    _validate_user_id(user_id)

    password_hash = hash_password(password, params=params)
    created_at_iso = _now_utc_iso()

    try:
        conn.execute(
            "INSERT INTO users (user_id, password_hash, actor_role, disabled, created_at) "
            "VALUES (?, ?, ?, 0, ?)",
            (user_id, password_hash, actor_role, created_at_iso),
        )
    except sqlite3.IntegrityError as exc:
        # PRIMARY KEY violation = user already exists per PB-30.
        if "UNIQUE" in str(exc) or "PRIMARY KEY" in str(exc):
            raise UserAlreadyExistsError(user_id) from exc
        raise  # Any other IntegrityError (e.g., CHECK violation) propagates.

    # Audit row in the same transaction per ADR-0013 §Decision.
    write_audit(
        conn,
        actor=audit_actor,
        event=EVT_ADMIN_CREATE_USER,
        target=user_id,
        extra={"actor_role": actor_role},
    )
    conn.commit()

    return User(
        user_id=user_id,
        actor_role=actor_role,
        disabled=False,
        created_at=datetime.fromisoformat(created_at_iso.replace("Z", "+00:00")),
    )


def list_users(conn: sqlite3.Connection) -> list[User]:
    """
    SELECT all users; return ``list[User]`` sorted by ``user_id``.

    Per Phase 18 PB-24 — never includes ``password_hash`` (the User
    dataclass has no such field, so it cannot leak even by accident).
    """
    rows = conn.execute(
        "SELECT user_id, actor_role, disabled, created_at "
        "FROM users ORDER BY user_id"
    ).fetchall()
    return [
        User(
            user_id=row[0],
            actor_role=row[1],
            disabled=bool(row[2]),
            created_at=datetime.fromisoformat(row[3].replace("Z", "+00:00")),
        )
        for row in rows
    ]


def verify(
    conn: sqlite3.Connection,
    user_id: str,
    password: str,
    *,
    params: Argon2Params,
) -> User:
    """
    Verify credentials. Returns :class:`User` on success; raises
    :class:`AuthFailedError` on any failure.

    **Phase 19 PB-9 / ADR-0013 §amendment-1 revision:** pure predicate.
    Does NOT write any audit row. The Phase 18 shape baked
    ``EVT_LOGIN_FAILED`` into this function, which produced a
    semantically wrong event when ``kill_my_own_sessions`` (Phase 19
    ADR-0005 escape valve) called verify() to gate a recovery action.
    Callers (:func:`mindsos_server.sessions.login` +
    :func:`mindsos_server.sessions.kill_my_own_sessions`) now own the
    audit emission and write the correct event for their context.

    Failure causes (all surface as :class:`AuthFailedError` with private
    ``.cause`` per Phase 18 PB-23):

    * :attr:`AuthFailureCause.UNKNOWN_USER` — no row for ``user_id``.
      Closes the timing leak by running argon2id against
      :data:`_SENTINEL_HASH` per Phase 18 PB-22 + PB-31 before raising.
    * :attr:`AuthFailureCause.BAD_PASSWORD` — row exists but argon2
      verify returned False.
    * :attr:`AuthFailureCause.DISABLED` — row exists, password correct,
      but ``disabled = 1`` per Phase 18 PB-15.

    Per PB-23, the exception's public message is uniform; callers
    cannot distinguish causes without inspecting ``.cause``. Callers
    that want to audit MUST inspect ``.cause`` and write the audit row
    themselves in the same transaction (per ADR-0013 §Decision "same
    SQLite transaction as the state change where feasible").
    """
    _validate_user_id(user_id)

    row = conn.execute(
        "SELECT password_hash, actor_role, disabled, created_at "
        "FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    if row is None:
        # Phase 18 PB-22: close timing leak by running argon2 against
        # sentinel hash. Same wall-clock cost as a real verify-fail.
        verify_against_sentinel(password, params=params)
        raise AuthFailedError(AuthFailureCause.UNKNOWN_USER)

    password_hash, actor_role, disabled, created_at_iso = row

    if not verify_password(password_hash, password, params=params):
        raise AuthFailedError(AuthFailureCause.BAD_PASSWORD)

    if bool(disabled):
        # Phase 18 PB-15: verify honors disabled. Password was correct but
        # the account is disabled; surface as auth failure (single
        # exception per PB-23) with private cause for caller audit.
        raise AuthFailedError(AuthFailureCause.DISABLED)

    return User(
        user_id=user_id,
        actor_role=actor_role,
        disabled=False,
        created_at=datetime.fromisoformat(created_at_iso.replace("Z", "+00:00")),
    )


# ---------------------------------------------------------------------------
# Bootstrap helper
# ---------------------------------------------------------------------------


def _insert_first_admin(
    conn: sqlite3.Connection,
    user_id: str,
    password: str,
    *,
    params: Argon2Params,
    os_user: str,
) -> User:
    """
    Bootstrap first-admin helper per Phase 18 PB-9 + PB-29 (PB-27 lift).

    Pure insert with ``actor_role='admin'``. Does NOT check whether
    admins already exist — the CLI caller (``mindsos server bootstrap``)
    owns that idempotency check per PB-29.

    Audit row uses the OS user as actor per ADR-0012 §Decision (no
    Session at bootstrap time).

    Raises :class:`UserAlreadyExistsError` on UNIQUE conflict — CLI
    caller should have skipped via the count-admins check first, so
    this would indicate a race or a misuse.

    Args:
        conn: SQLite connection.
        user_id: Admin user_id.
        password: Plaintext password (will be argon2id-hashed).
        params: argon2id parameters.
        os_user: OS user invoking bootstrap (typically from
            ``pwd.getpwuid(os.getuid()).pw_name``); written as
            ``actor_user`` on the ``EVT_BOOTSTRAP`` audit row.

    Returns:
        :class:`User` view of the inserted admin.
    """
    _validate_user_id(user_id)

    password_hash = hash_password(password, params=params)
    created_at_iso = _now_utc_iso()

    try:
        conn.execute(
            "INSERT INTO users (user_id, password_hash, actor_role, disabled, created_at) "
            "VALUES (?, ?, 'admin', 0, ?)",
            (user_id, password_hash, created_at_iso),
        )
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" in str(exc) or "PRIMARY KEY" in str(exc):
            raise UserAlreadyExistsError(user_id) from exc
        raise

    # Bootstrap audit row uses OS user as actor per ADR-0012.
    # Local import to avoid circular: audit constants are in audit.py.
    from mindsos_server.audit import EVT_BOOTSTRAP

    write_audit(
        conn,
        actor=os_user,
        event=EVT_BOOTSTRAP,
        target=user_id,
        extra={"actor_role": "admin"},
    )
    conn.commit()

    return User(
        user_id=user_id,
        actor_role="admin",
        disabled=False,
        created_at=datetime.fromisoformat(created_at_iso.replace("Z", "+00:00")),
    )


def count_admins(conn: sqlite3.Connection) -> int:
    """
    Count active admin rows.

    Used by the bootstrap CLI verb per PB-29 to enforce idempotency
    (skip with exit-0 message if ``≥1`` active admin already exists).

    "Active" = ``disabled = 0``. A disabled admin does NOT count toward
    the "system has admins" invariant (Phase 20 last-admin protection
    enforces the same definition).
    """
    row = conn.execute(
        "SELECT COUNT(*) FROM users WHERE actor_role = 'admin' AND disabled = 0"
    ).fetchone()
    return int(row[0])
