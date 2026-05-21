"""
Session management — login, logout, session_from_token,
kill_my_own_sessions per Phase 19.

Free-function surface per Phase 19 PB-13 (the ``MindsOSServer``
orchestrator class is deferred to Phase 25 per ADR-0011 §amendment-1).
TTL injection via explicit kwarg per PB-15 (mirrors Phase 18 PB-14's
``Argon2Params`` pattern; no module-level global, no env-driven
state — tests pass ``_TEST_FAST_TTL`` per call).

Architecture summary:

* **Token shape:** ``secrets.token_urlsafe(32)`` → 256-bit opaque,
  URL-safe, unpredictable per ADR-0003. The plaintext token is the
  caller's auth material; the server stores only its SHA-256 hash.
* **Session id shape:** ``secrets.token_urlsafe(16)`` → 128-bit opaque
  per Phase 19 minor lock. Separate primitive from the token —
  never derivable from it. Admins copy session_ids from audit rows
  for Phase 22's ``admin_kill_session``.
* **TTL shape per ADR-0003 + ADR-0004 §am1:** sliding 8h from
  ``last_seen_at``; absolute 24h from ``created_at``. ``expires_at`` is
  computed at lookup (NOT stored — PB-10 / ADR-0004 §am1).
* **Login ordering per ADR-0005 §am1 PB-8:** lazy-expire any stale
  session for the user_id → check for any remaining → if exists
  raise :class:`AlreadyLoggedInError` → else mint new.
* **Lookup behavior per ADR-0003 §am1:** SQLite indexed equality
  (``WHERE token_hash = ?``); the "constant-time comparison" §Decision
  clause was dropped at Phase 19 ship as misleading — 256-bit SHA-256
  preimage resistance dominates.
* **Exception shape per Phase 19 PB-14:** single
  :class:`InvalidSessionError` with private cause enum unifies
  expired-sliding / expired-absolute / not-found.
* **CLI-only product per ADR-0005 §am1 PB-1:** sessions persist across
  CLI invocations and die on lazy TTL expiry, explicit logout, or
  manual ``server.db`` deletion. The "wipe on server restart"
  invariant is scoped to a future HTTP daemon phase.

This module does NOT export anything except via
``mindsos_server/__init__.py``. All cross-module imports happen at the
top of file (no circular-import lazy imports) — sessions.py depends on
``mindsos_server.audit``, ``mindsos_server.errors``,
``mindsos_server.session`` (the dataclass), ``mindsos_server.users``,
``mindsos_server._argon2``.

Per Phase 19 PB-2 / ADR-0011 §am1: this module does NOT hydrate Locals
on login. The ``LocalPersister`` + KL hydration land at Phase 25;
``login()``'s signature is forward-compatible (Phase 25 adds
``persister`` + ``kl`` as kwargs with defaults).
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from mindsos_server._argon2 import Argon2Params, PRODUCTION_PARAMS
from mindsos_server.audit import (
    EVT_LOGIN,
    EVT_LOGIN_FAILED,
    EVT_LOGIN_REJECTED_CONCURRENT,
    EVT_LOGOUT,
    _now_utc_iso,
    write_audit,
)
from mindsos_server.capabilities import ADMIN_CAPS, USER_CAPS
from mindsos_server.errors import (
    AlreadyLoggedInError,
    AuthFailedError,
    InvalidSessionCause,
    InvalidSessionError,
)
from mindsos_server.session import Session
from mindsos_server.users import User, verify


# ---------------------------------------------------------------------------
# TTL configuration (Phase 19 PB-12 + PB-15)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SessionTTL:
    """
    Sliding + absolute TTL parameters per ADR-0003 §Decision (sliding
    8h + absolute 24h) + Phase 19 PB-12 (test-fast variant for the
    suite — 1s / 2s; mirrors Phase 18 PB-14's ``_TEST_FAST_PARAMS``).

    Per Phase 19 PB-15 — injected as explicit kwarg on every call site
    that needs it (``login`` / ``session_from_token`` /
    ``kill_my_own_sessions``). No module-level global; no env-driven
    state. Mirrors Phase 18 PB-14's anti-global precedent.

    Units: seconds (int). Storing as int keeps the SessionTTL hashable
    and the math straightforward (created_at + timedelta(seconds=N)).
    """

    #: Sliding window — session valid if
    #: ``now - last_seen_at < sliding_seconds``.
    sliding_seconds: int

    #: Absolute window — session valid if
    #: ``now - created_at < absolute_seconds``. Hard ceiling regardless
    #: of activity per ADR-0003 §Rationale.
    absolute_seconds: int


#: Production TTL per ADR-0003 §Decision verbatim — sliding 8h,
#: absolute 24h.
PRODUCTION_TTL = SessionTTL(
    sliding_seconds=8 * 3600,
    absolute_seconds=24 * 3600,
)

#: Test-fast TTL per Phase 19 PB-12. 1-second sliding, 2-second
#: absolute lets the test suite exercise both expiry paths within the
#: pytest-suite latency budget. Mirrors Phase 18 PB-14's
#: ``_TEST_FAST_PARAMS`` underscore-prefix convention (test-only;
#: review catches stray production usage).
_TEST_FAST_TTL = SessionTTL(
    sliding_seconds=1,
    absolute_seconds=2,
)


# ---------------------------------------------------------------------------
# Return type for login (Phase 19 PB-6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LoginResult:
    """
    Return shape of :func:`login` per Phase 19 PB-6.

    Bundles the Session object (which stays bare per Phase 18 PB-33 —
    only ``session_id`` / ``user_id`` / ``actor_role`` / ``capabilities``)
    with the timestamps + plaintext token the caller needs. The
    timestamps are NOT on Session because (a) ADR-0040's
    SessionProtocol parity stays trivial (KL never needs them) and
    (b) the source of truth for timestamps is the ``sessions`` row.

    ``expires_at`` is the computed-at-issue absolute-cap-bounded sliding
    expiry: ``min(created_at + ttl.absolute, created_at + ttl.sliding)``
    at issue == ``created_at + ttl.sliding`` (since
    ``last_seen_at = created_at`` at issue). Subsequent
    :func:`session_from_token` calls advance ``last_seen_at`` and
    therefore the computed expires_at; the returned value here is the
    expires_at at moment of issue.

    The plaintext ``token`` is returned to the caller. The server
    stores only its SHA-256 hash. The CLI persists it per PB-5
    (file 0600 + env override).
    """

    session: Session
    token: str
    created_at: datetime
    expires_at: datetime


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _hash_token(token: str) -> str:
    """
    SHA-256 hex digest of the plaintext token per ADR-0003.

    Per ADR-0003 §amendment-1 (Phase 19 PB-7): SQLite indexed equality
    on this hex digest is the lookup mechanism — the original ADR
    §Decision "constant-time comparison" wording was dropped as
    misleading. 256-bit SHA-256 preimage resistance dominates any
    plausible timing-attack model on indexed equality.
    """
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _mint_session_id() -> str:
    """
    Generate a fresh session_id per Phase 19 minor lock.

    128-bit opaque random via ``secrets.token_urlsafe(16)`` — separate
    primitive from the 256-bit token. Admins copy session_ids from
    audit rows for Phase 22's ``admin_kill_session``; the id is never
    derivable from the token.
    """
    return secrets.token_urlsafe(16)


def _mint_token() -> str:
    """
    Generate a fresh session token per ADR-0003.

    256-bit opaque random via ``secrets.token_urlsafe(32)`` — URL-safe,
    unpredictable. Returned plaintext to the caller; server stores
    only the SHA-256 hash (see :func:`_hash_token`).
    """
    return secrets.token_urlsafe(32)


def _parse_iso(ts: str) -> datetime:
    """
    Parse the canonical TEXT ISO-8601 UTC ms format produced by
    :func:`mindsos_server.audit._now_utc_iso`.

    Format: ``YYYY-MM-DDTHH:MM:SS.mmmZ`` per Phase 18 PB-35. We swap
    the trailing ``Z`` to ``+00:00`` for :meth:`datetime.fromisoformat`
    compatibility on Python 3.10. Python 3.11+ accepts ``Z`` directly;
    the swap is a no-cost compatibility shim for now.
    """
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _expires_at(
    created_at: datetime,
    last_seen_at: datetime,
    ttl: SessionTTL,
) -> datetime:
    """
    Compute the effective expiry timestamp per ADR-0004 §amendment-1
    (Phase 19 PB-10 — expires_at is NOT stored; computed at lookup).

    Returns ``min(created_at + ttl.absolute_seconds, last_seen_at + ttl.sliding_seconds)``.
    """
    absolute = created_at + timedelta(seconds=ttl.absolute_seconds)
    sliding = last_seen_at + timedelta(seconds=ttl.sliding_seconds)
    return min(absolute, sliding)


def _classify_expiry(
    created_at: datetime,
    last_seen_at: datetime,
    ttl: SessionTTL,
    now: datetime,
) -> InvalidSessionCause | None:
    """
    Return the relevant :class:`InvalidSessionCause` if the session is
    expired, else ``None``.

    Per ADR-0003 §Rationale + InvalidSessionCause.EXPIRED_ABSOLUTE
    docstring: the absolute cap takes precedence when both apply (the
    absolute is the harder limit). If only sliding applies, return
    EXPIRED_SLIDING. If neither, return None.
    """
    absolute_deadline = created_at + timedelta(seconds=ttl.absolute_seconds)
    sliding_deadline = last_seen_at + timedelta(seconds=ttl.sliding_seconds)

    if now >= absolute_deadline:
        return InvalidSessionCause.EXPIRED_ABSOLUTE
    if now >= sliding_deadline:
        return InvalidSessionCause.EXPIRED_SLIDING
    return None


def _capabilities_for_role(actor_role: str) -> frozenset[str]:
    """
    Map ``actor_role`` from the users row to the capability set per
    ADR-0002.

    Phase 18 PB-12: USER_CAPS strictly empty in v1 (Proposed-status
    caps from ADR-0118 / ADR-0137 defer to their Accept-flip phase).
    ADMIN_CAPS is all 7 ADR-0002 constants.
    """
    if actor_role == "admin":
        return ADMIN_CAPS
    return USER_CAPS


def _utc_now() -> datetime:
    """
    Wall-clock ``datetime`` in UTC, matching the precision of
    :func:`mindsos_server.audit._now_utc_iso` (millisecond). Used for
    expiry comparisons; sub-second resolution matters when
    ``_TEST_FAST_TTL`` runs the suite with 1-second sliding window.
    """
    from datetime import UTC

    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Login (Phase 19 PB-6 + PB-8 + PB-9 + PB-15)
# ---------------------------------------------------------------------------


def login(
    conn: sqlite3.Connection,
    user_id: str,
    password: str,
    *,
    ttl: SessionTTL = PRODUCTION_TTL,
    params: Argon2Params = PRODUCTION_PARAMS,
) -> LoginResult:
    """
    Authenticate and issue a session.

    Algorithm:

    1. Call :func:`mindsos_server.users.verify` (pure predicate per
       PB-9). On :class:`AuthFailedError`, write ``EVT_LOGIN_FAILED``
       audit + re-raise (callers own the audit emission per ADR-0013
       §amendment-1).
    2. Per ADR-0005 §amendment-1 §Consequences (PB-8 ordering lock):
       lazy-expire-then-concurrent-check-then-mint.
       (a) DELETE any session row for ``user_id`` whose computed
       expiry is in the past.
       (b) If any session row for ``user_id`` remains, write
       ``EVT_LOGIN_REJECTED_CONCURRENT`` audit + raise
       :class:`AlreadyLoggedInError` with 2-field payload per PB-3.
       (c) Else mint new ``session_id`` + token + insert sessions row
       + write ``EVT_LOGIN`` audit (all in one SQLite transaction per
       ADR-0013).

    Args:
        conn: SQLite connection from :func:`mindsos_server._db.open_db`.
        user_id: Charset-validated by verify().
        password: Plaintext.
        ttl: SessionTTL; defaults to :data:`PRODUCTION_TTL`. Tests pass
            :data:`_TEST_FAST_TTL` per Phase 19 PB-12.
        params: argon2id parameters; defaults to
            :data:`mindsos_server._argon2.PRODUCTION_PARAMS`. Tests
            pass ``_TEST_FAST_PARAMS`` per Phase 18 PB-14.

    Raises:
        AuthFailedError: from verify() — credentials reject. ``EVT_LOGIN_FAILED``
            audit written before re-raising.
        AlreadyLoggedInError: an active (non-expired) session already
            exists for this user_id. ``EVT_LOGIN_REJECTED_CONCURRENT``
            audit written before raising.

    Returns:
        :class:`LoginResult` carrying the Session, plaintext token,
        and timestamps.
    """
    try:
        user = verify(conn, user_id, password, params=params)
    except AuthFailedError as exc:
        # PB-9 / ADR-0013 §am1: caller owns the audit. verify() no
        # longer writes EVT_LOGIN_FAILED; this is the login-context
        # audit emission. extra_json carries the private cause for
        # Phase 21 admin audit readers.
        write_audit(
            conn,
            actor=user_id,
            event=EVT_LOGIN_FAILED,
            target=user_id,
            extra={"cause": exc.cause.value},
        )
        conn.commit()
        raise

    now = _utc_now()

    # Step (a): lazy-expire any stale session for this user.
    # Per ADR-0005 §am1 §Consequences (PB-8) — MUST run before the
    # concurrent-login check, else a stale session locks out the
    # caller for no reason.
    _lazy_expire_user_sessions(conn, user_id, ttl=ttl, now=now)

    # Step (b): concurrent-login check against remaining (non-expired)
    # sessions.
    existing = conn.execute(
        "SELECT session_id, created_at FROM sessions WHERE user_id = ? LIMIT 1",
        (user_id,),
    ).fetchone()

    if existing is not None:
        existing_session_id, existing_created_at = existing
        write_audit(
            conn,
            actor=user_id,
            event=EVT_LOGIN_REJECTED_CONCURRENT,
            target=user_id,
            extra={
                "existing_session_id": existing_session_id,
                "existing_created_at": existing_created_at,
            },
        )
        conn.commit()
        raise AlreadyLoggedInError(
            existing_session_id=existing_session_id,
            created_at=existing_created_at,
        )

    # Step (c): mint + insert + audit, all in one transaction.
    session_id = _mint_session_id()
    token = _mint_token()
    token_hash = _hash_token(token)
    created_at_iso = _now_utc_iso()
    # Initialize last_seen_at to created_at on issue.

    conn.execute(
        "INSERT INTO sessions "
        "(session_id, user_id, token_hash, created_at, last_seen_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (session_id, user_id, token_hash, created_at_iso, created_at_iso),
    )
    write_audit(
        conn,
        actor=user_id,
        event=EVT_LOGIN,
        target=user_id,
        extra={"session_id": session_id},
    )
    conn.commit()

    capabilities = _capabilities_for_role(user.actor_role)
    session = Session(
        session_id=session_id,
        user_id=user_id,
        actor_role=user.actor_role,
        capabilities=capabilities,
    )

    created_at_dt = _parse_iso(created_at_iso)
    expires_at_dt = _expires_at(created_at_dt, created_at_dt, ttl)

    return LoginResult(
        session=session,
        token=token,
        created_at=created_at_dt,
        expires_at=expires_at_dt,
    )


def _lazy_expire_user_sessions(
    conn: sqlite3.Connection,
    user_id: str,
    *,
    ttl: SessionTTL,
    now: datetime,
) -> int:
    """
    Delete any session row for ``user_id`` whose computed expiry is in
    the past. Helper for the PB-8 ordering lock at the top of
    :func:`login`.

    Does NOT commit — caller (login) owns the transaction boundary.

    Returns:
        Number of rows deleted (for tests + future debug).
    """
    rows = conn.execute(
        "SELECT session_id, created_at, last_seen_at FROM sessions "
        "WHERE user_id = ?",
        (user_id,),
    ).fetchall()

    expired_ids = [
        row[0]
        for row in rows
        if _classify_expiry(
            _parse_iso(row[1]),
            _parse_iso(row[2]),
            ttl,
            now,
        )
        is not None
    ]

    if expired_ids:
        # SQLite has no IN-clause cap below 999; safe for any realistic
        # session count per user (which should always be 0 or 1 in
        # well-behaved use).
        placeholders = ",".join("?" * len(expired_ids))
        conn.execute(
            f"DELETE FROM sessions WHERE session_id IN ({placeholders})",
            expired_ids,
        )

    return len(expired_ids)


# ---------------------------------------------------------------------------
# session_from_token (Phase 19 PB-8 ordering + PB-14 InvalidSessionError)
# ---------------------------------------------------------------------------


def session_from_token(
    conn: sqlite3.Connection,
    token: str,
    *,
    ttl: SessionTTL = PRODUCTION_TTL,
) -> Session:
    """
    Resolve a token to a :class:`Session`.

    Algorithm:

    1. SHA-256 the token; SELECT the matching sessions row by
       indexed equality per ADR-0003 §amendment-1.
    2. If no row: raise :class:`InvalidSessionError` with
       :attr:`InvalidSessionCause.NOT_FOUND`.
    3. Else compute expiry. If expired: DELETE the row (lazy
       expiry per ADR-0003 §am1) + commit + raise
       :class:`InvalidSessionError` with the appropriate cause.
    4. Else UPDATE ``last_seen_at = now`` (sliding-TTL refresh per
       ADR-0003 §Decision) + commit + return the constructed Session.

    The Session returned matches ADR-0040 SessionProtocol verbatim
    (Phase 18 PB-33). Timestamps + token are NOT on Session; callers
    that need them keep their LoginResult from login().

    Args:
        conn: SQLite connection.
        token: Plaintext 256-bit token from CLI / future HTTP header.
        ttl: SessionTTL; defaults to :data:`PRODUCTION_TTL`.

    Raises:
        InvalidSessionError: any of the three causes per PB-14.

    Returns:
        :class:`Session` with capabilities resolved from the user's
        ``actor_role`` at lookup time. (Capabilities are NOT cached
        on the sessions row — looked up fresh from users on each call
        so admin role changes via Phase 22 take effect on the next
        lookup, not after token renewal.)
    """
    token_hash = _hash_token(token)

    row = conn.execute(
        "SELECT s.session_id, s.user_id, s.created_at, s.last_seen_at, "
        "       u.actor_role "
        "FROM sessions s JOIN users u ON s.user_id = u.user_id "
        "WHERE s.token_hash = ?",
        (token_hash,),
    ).fetchone()

    if row is None:
        raise InvalidSessionError(InvalidSessionCause.NOT_FOUND)

    session_id, user_id, created_at_iso, last_seen_at_iso, actor_role = row
    created_at = _parse_iso(created_at_iso)
    last_seen_at = _parse_iso(last_seen_at_iso)

    now = _utc_now()
    expiry_cause = _classify_expiry(created_at, last_seen_at, ttl, now)

    if expiry_cause is not None:
        # Lazy expiry per ADR-0003 §am1: DELETE the stale row inline
        # before raising. Future identical lookups will get
        # NOT_FOUND instead of EXPIRED_*.
        conn.execute(
            "DELETE FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        conn.commit()
        raise InvalidSessionError(expiry_cause)

    # Sliding-TTL refresh: bump last_seen_at on successful lookup.
    new_last_seen_iso = _now_utc_iso()
    conn.execute(
        "UPDATE sessions SET last_seen_at = ? WHERE session_id = ?",
        (new_last_seen_iso, session_id),
    )
    conn.commit()

    return Session(
        session_id=session_id,
        user_id=user_id,
        actor_role=actor_role,
        capabilities=_capabilities_for_role(actor_role),
    )


# ---------------------------------------------------------------------------
# Logout (Phase 19 PB-11)
# ---------------------------------------------------------------------------


def logout(conn: sqlite3.Connection, token: str) -> bool:
    """
    Delete the session row matching ``token``.

    Per Phase 19 PB-11 — self-logout is by-token (not by-session_id).
    The caller possesses the token by definition; requiring a separate
    session_id round-trip adds nothing.

    Per Phase 19 minor lock — invalid / expired / missing token is a
    silent no-op (exit 0 at CLI). Logout is idempotent by nature; no
    ``EVT_LOGOUT_FAILED`` audit constant.

    Args:
        conn: SQLite connection.
        token: Plaintext token from the caller.

    Returns:
        True if a row was actually deleted; False otherwise.
        ``EVT_LOGOUT`` audit is written only on successful deletion;
        the audit row carries the deleted session_id in extra_json.
    """
    token_hash = _hash_token(token)

    row = conn.execute(
        "SELECT session_id, user_id FROM sessions WHERE token_hash = ?",
        (token_hash,),
    ).fetchone()

    if row is None:
        return False

    session_id, user_id = row

    conn.execute(
        "DELETE FROM sessions WHERE session_id = ?",
        (session_id,),
    )
    write_audit(
        conn,
        actor=user_id,
        event=EVT_LOGOUT,
        target=user_id,
        extra={"session_id": session_id},
    )
    conn.commit()

    return True


# ---------------------------------------------------------------------------
# kill_my_own_sessions (Phase 19 ADR-0005 escape valve + PB-9)
# ---------------------------------------------------------------------------


def kill_my_own_sessions(
    conn: sqlite3.Connection,
    user_id: str,
    password: str,
    *,
    ttl: SessionTTL = PRODUCTION_TTL,
    params: Argon2Params = PRODUCTION_PARAMS,
) -> int:
    """
    Self-recovery escape valve per ADR-0005.

    Takes **fresh credentials** (not a token — by definition the caller
    has lost / wedged their session and cannot present a valid token).
    Calls verify() to gate the action; on success, DELETEs every
    session row for that user_id (regardless of expiry state) and
    writes one ``EVT_LOGOUT`` audit row per killed session.

    Per Phase 19 PB-9 / ADR-0013 §am1: this function owns its audit
    emission. On verify() failure, writes ``EVT_LOGIN_FAILED`` (with
    private cause in extra_json) and re-raises — same shape as login
    failure, since the caller's intent is to recover *via login-style
    credentials*. A future amendment may distinguish
    ``EVT_KILL_SESSIONS_FAILED`` if audit-differential becomes
    important.

    Per ADR-0005 §am1 §Consequences: deletes ALL rows for the user
    regardless of expiry state (a stale session being deleted as part
    of a recovery is correct — no GC concern).

    Args:
        conn: SQLite connection.
        user_id: User to kill sessions for.
        password: Fresh credentials.
        ttl: SessionTTL — unused for the delete path (no expiry math),
            kept in the signature for API uniformity with login() /
            session_from_token().
        params: argon2id parameters.

    Raises:
        AuthFailedError: from verify() — credentials reject. Audit
            written before re-raising.

    Returns:
        Number of sessions actually killed. 0 is valid (user had no
        sessions; the call is still a successful recovery — verify
        succeeded).
    """
    # Suppress unused-var warning while keeping signature uniform.
    _ = ttl

    try:
        verify(conn, user_id, password, params=params)
    except AuthFailedError as exc:
        write_audit(
            conn,
            actor=user_id,
            event=EVT_LOGIN_FAILED,
            target=user_id,
            extra={
                "cause": exc.cause.value,
                "context": "kill_my_own_sessions",
            },
        )
        conn.commit()
        raise

    # Fetch session_ids first so we can audit one EVT_LOGOUT per row
    # before the DELETE. Per ADR-0013 §Decision "same transaction".
    rows = conn.execute(
        "SELECT session_id FROM sessions WHERE user_id = ?",
        (user_id,),
    ).fetchall()

    if not rows:
        return 0

    session_ids = [row[0] for row in rows]

    conn.execute(
        "DELETE FROM sessions WHERE user_id = ?",
        (user_id,),
    )

    for session_id in session_ids:
        write_audit(
            conn,
            actor=user_id,
            event=EVT_LOGOUT,
            target=user_id,
            extra={
                "session_id": session_id,
                "context": "kill_my_own_sessions",
            },
        )

    conn.commit()

    return len(session_ids)
