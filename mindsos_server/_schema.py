"""
SQLite schema + forward-only migration framework for ``server.db``.

Phase 18 shipped **schema v1** with two tables (``users`` + ``audit``)
+ the ``schema_version`` tracking row. **Phase 19 ships schema v2**
adding the ``sessions`` table (PB-10 5-column shape per ADR-0004 §am1:
no stored ``expires_at`` — computed at lookup from
``min(created_at + ttl.absolute, last_seen_at + ttl.sliding)``).

Migration framework per Phase 18 PB-2:

* Forward-only DDL.
* One ``schema_version`` row tracks the current version integer.
* :func:`init_or_migrate` is idempotent: safe to call on a fresh DB
  (creates everything) or an already-migrated DB (no-op). Future
  migrations append a new DDL block + bump the ``_SCHEMA_VERSION``
  constant + add an upgrade step.

No external migration framework (no Alembic, no yoyo) per PB-2: the
three-table v2 schema does not justify the dep + tooling overhead.

Phase 18 PB-19 — every connection that touches ``server.db`` MUST be
opened via :func:`mindsos_server._db.open_db` which sets the WAL +
foreign_keys + busy_timeout pragmas. :func:`init_or_migrate` assumes
those pragmas are in effect on the passed connection. The ``sessions``
table relies on ``foreign_keys=ON`` for its
``REFERENCES users(user_id) ON DELETE CASCADE`` constraint to fire at
Phase 22's ``hard_delete_user``.
"""

from __future__ import annotations

import sqlite3

#: Current schema version. Bump in lockstep with adding a new migration
#: step in :func:`init_or_migrate`. Phase 18 = 1 (users + audit); Phase
#: 19 = 2 (adds sessions per PB-10); Phase 21 = 3 (adds idx_audit_target
#: per PB-7 — separate ``target=`` filter kwarg in
#: :func:`mindsos_server.admin.admin_query_audit` made ``WHERE
#: target_user = ?`` a first-class query shape per ADR-0013 §am2).
_SCHEMA_VERSION: int = 3


# ---------------------------------------------------------------------------
# DDL — schema v1 (Phase 18)
# ---------------------------------------------------------------------------

#: ``schema_version`` tracker. Single-row design — there's exactly one
#: row whose ``version`` column holds the current integer. ``key`` is a
#: redundant marker (always 'schema_version') used as the PK so the
#: single-row invariant is enforceable via ``INSERT OR REPLACE``.
_DDL_SCHEMA_VERSION = """
CREATE TABLE IF NOT EXISTS schema_version (
    key TEXT PRIMARY KEY,
    version INTEGER NOT NULL
)
"""

#: ``users`` table per ADR-0004 + Phase 18 PB-16 (``user_id TEXT
#: PRIMARY KEY``) + PB-28 (``actor_role`` CHECK constraint) + PB-35
#: (TEXT ISO-8601 UTC timestamps).
#:
#: Columns:
#:
#: * ``user_id`` — charset-constrained per ADR-0044 §amendment-1; regex
#:   enforced at insert time by :func:`mindsos_server.users.insert_user`.
#: * ``password_hash`` — ``$argon2id$...`` encoded hash per ADR-0003.
#: * ``actor_role`` — ``'user'`` | ``'admin'``; CHECK constraint.
#: * ``disabled`` — INTEGER 0/1; verify() honors per Phase 18 PB-15.
#:   Phase 22 ships the disable/enable CLI verbs.
#: * ``created_at`` — TEXT ISO-8601 UTC ms per PB-35 (use
#:   :func:`mindsos_server.audit._now_utc_iso`).
_DDL_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id        TEXT PRIMARY KEY,
    password_hash  TEXT NOT NULL,
    actor_role     TEXT NOT NULL CHECK (actor_role IN ('user', 'admin')),
    disabled       INTEGER NOT NULL DEFAULT 0 CHECK (disabled IN (0, 1)),
    created_at     TEXT NOT NULL
)
"""

#: ``audit`` table per ADR-0013 + Phase 18 PB-11 (ships at v1, not v3).
#:
#: Schema is stable per ADR-0013 §Rationale ("JSON extras, not columns"):
#: new event types add new keys to ``extra_json``, not new columns.
#:
#: Columns:
#:
#: * ``id`` — INTEGER PK; AUTOINCREMENT not needed (rowid is monotonic
#:   per SQLite spec).
#: * ``ts`` — TEXT ISO-8601 UTC ms per PB-35; sortable lexicographically.
#: * ``actor_user`` — TEXT; user_id of the actor OR OS user (for
#:   ``EVT_BOOTSTRAP`` / ``EVT_RESET_ADMIN`` per ADR-0012 §Decision).
#:   Nullable to accommodate future system-actor events.
#: * ``event`` — TEXT; one of the constants in
#:   :mod:`mindsos_server.audit`.
#: * ``target_user`` — TEXT, nullable; user_id the event is *about*
#:   (e.g., ``EVT_ADMIN_CREATE_USER`` target is the created user).
#: * ``extra_json`` — TEXT; valid JSON object, includes
#:   event-specific fields (e.g., ``cause`` for auth failures,
#:   ``argon2_params`` summary for hashing events).
#:
#: No FK to ``users.user_id`` on ``actor_user`` or ``target_user``
#: because audit rows MUST outlive their subjects (hard-delete of a
#: user MUST NOT cascade-delete their audit trail per ADR-0013
#: §Consequences "Audit table growth is unbounded by design").
_DDL_AUDIT = """
CREATE TABLE IF NOT EXISTS audit (
    id           INTEGER PRIMARY KEY,
    ts           TEXT NOT NULL,
    actor_user   TEXT,
    event        TEXT NOT NULL,
    target_user  TEXT,
    extra_json   TEXT NOT NULL DEFAULT '{}'
)
"""

#: Indexes on audit table for the Phase 21 reader query shapes.
#: Phase 18 shipped ts/event/actor; Phase 21 PB-7 + PB-19 adds target.
#:
#: PB-19 intentional duplication: ``idx_audit_target`` is ALSO added
#: via the v2→v3 migration block in :func:`init_or_migrate` to reach
#: existing-v2 installs. The duplication is drift-free because
#: ``CREATE INDEX IF NOT EXISTS`` is idempotent — a fresh-install
#: hitting the v0→v1 path creates all four indexes from this list,
#: and an existing-v2 install hitting the v2→v3 path creates only
#: ``idx_audit_target`` (the other three are already present from
#: the earlier v0→v1 run). Mirrors Phase 19's sessions-DDL-in-both-
#: paths pattern.
_DDL_AUDIT_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit(ts)",
    "CREATE INDEX IF NOT EXISTS idx_audit_event ON audit(event)",
    "CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit(actor_user)",
    "CREATE INDEX IF NOT EXISTS idx_audit_target ON audit(target_user)",
]


# ---------------------------------------------------------------------------
# DDL — schema v2 (Phase 19)
# ---------------------------------------------------------------------------

#: ``sessions`` table per ADR-0004 §amendment-1 + Phase 19 PB-10
#: (``expires_at`` computed at lookup, not stored — 5 columns) + PB-8
#: (lazy-expire-then-concurrent-check ordering enforced in code, not
#: schema) + PB-1 (sessions persist across CLI invocations — wipe-on-
#: restart is scoped to the future HTTP daemon phase via ADR-0005 §am1).
#:
#: Columns:
#:
#: * ``session_id`` — TEXT PK. Generated by
#:   :func:`mindsos_server.sessions._mint_session_id` via
#:   ``secrets.token_urlsafe(16)`` — 128-bit opaque random, separate
#:   primitive from the 256-bit token. Admins copy session_ids from
#:   audit rows; the id is never derivable from the token.
#: * ``user_id`` — TEXT NOT NULL. ``REFERENCES users(user_id) ON DELETE
#:   CASCADE`` — Phase 22's ``hard_delete_user`` cleanup is automatic
#:   when ``PRAGMA foreign_keys=ON`` (set in :func:`_db.open_db` per
#:   Phase 18 PB-19).
#: * ``token_hash`` — TEXT NOT NULL UNIQUE. SHA-256 hex digest of the
#:   plaintext 256-bit token per ADR-0003 + ADR-0003 §am1 (indexed
#:   equality lookup; the "constant-time comparison" clause was dropped
#:   as misleading — SQLite's indexed equality is the mechanism). UNIQUE
#:   constraint auto-indexes the lookup hot path.
#: * ``created_at`` — TEXT ISO-8601 UTC ms per Phase 18 PB-35 (use
#:   :func:`mindsos_server.audit._now_utc_iso`).
#: * ``last_seen_at`` — TEXT ISO-8601 UTC ms. Initialised to
#:   ``created_at`` at INSERT; bumped on every successful
#:   :func:`mindsos_server.sessions.session_from_token` lookup
#:   (sliding-TTL refresh).
#:
#: Phase 19 does NOT store ``expires_at`` per PB-10 — it is computed
#: lazily at lookup via
#: ``min(created_at + ttl.absolute_seconds, last_seen_at + ttl.sliding_seconds)``
#: and returned to callers in :class:`mindsos_server.sessions.LoginResult`
#: (PB-6). Storing the derived value would invite drift if last_seen_at
#: gets updated and expires_at doesn't.
_DDL_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id    TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash    TEXT NOT NULL UNIQUE,
    created_at    TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL
)
"""

#: Indexes on sessions table.
#:
#: The UNIQUE constraint on ``token_hash`` auto-indexes the
#: :func:`session_from_token` hot path (``SELECT ... WHERE token_hash = ?``).
#:
#: ``idx_sessions_user_id`` covers (a) the refuse-concurrent-login
#: lookup at login time (``SELECT 1 FROM sessions WHERE user_id = ?``
#: per PB-8 ordering), (b) the multi-row delete in
#: :func:`kill_my_own_sessions` (``DELETE FROM sessions WHERE
#: user_id = ?``), and (c) the parallel future Phase 20 ``reset-admin``
#: + Phase 22 ``admin_disable_user`` flush paths.
_DDL_SESSIONS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
]


# ---------------------------------------------------------------------------
# Migration framework
# ---------------------------------------------------------------------------


def init_or_migrate(conn: sqlite3.Connection) -> int:
    """
    Initialize a fresh ``server.db`` or migrate an existing one forward.

    Idempotent: safe to call multiple times. On a fresh DB creates
    everything; on a v1 DB does nothing (returns current version);
    future migrations (v1→v2 at Phase 19, etc.) will branch on the
    current version and run upgrade steps.

    Returns the schema version after migration.

    Caller responsibility (Phase 18 PB-19): the connection must have
    WAL + foreign_keys=ON + busy_timeout already set. Use
    :func:`mindsos_server._db.open_db` to get such a connection.

    Migration step ordering MUST be append-only: every new version
    branch goes at the end. Past steps are immutable history.
    """
    # Create the schema_version tracker if it doesn't exist (v0 → v1 case
    # OR first call on a fresh DB).
    conn.execute(_DDL_SCHEMA_VERSION)
    conn.commit()

    current = _read_version(conn)

    # v0 → v1: ship the Phase 18 schema (users + audit + indexes).
    if current < 1:
        conn.execute(_DDL_USERS)
        conn.execute(_DDL_AUDIT)
        for index_ddl in _DDL_AUDIT_INDEXES:
            conn.execute(index_ddl)
        _write_version(conn, 1)
        conn.commit()
        current = 1

    # v1 → v2: ship the Phase 19 sessions table + index per PB-10.
    # No data migration needed — sessions starts empty; existing users
    # + audit rows are untouched.
    if current < 2:
        conn.execute(_DDL_SESSIONS)
        for index_ddl in _DDL_SESSIONS_INDEXES:
            conn.execute(index_ddl)
        _write_version(conn, 2)
        conn.commit()
        current = 2

    # v2 → v3: ship the Phase 21 idx_audit_target index per PB-7.
    # Separate ``target=`` kwarg in
    # :func:`mindsos_server.admin.admin_query_audit` (ADR-0013 §am2)
    # made ``WHERE target_user = ?`` a first-class query shape; no
    # index existed at v2.
    #
    # PB-19 intentional duplication: this same index is also in
    # ``_DDL_AUDIT_INDEXES`` for fresh-install v0→v1 path. Drift-free
    # because ``CREATE INDEX IF NOT EXISTS`` is idempotent (the
    # cross-path conjunction always produces the same final state).
    # No data migration needed — audit rows are unaffected.
    if current < 3:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_target ON audit(target_user)"
        )
        _write_version(conn, 3)
        conn.commit()
        current = 3

    return current


def _read_version(conn: sqlite3.Connection) -> int:
    """
    Read the current schema_version. Returns 0 if no row exists
    (pre-v1 state — either a brand-new DB or one that pre-dates the
    migration framework, which won't happen in practice since v1 is
    Phase 18's first ship).
    """
    row = conn.execute(
        "SELECT version FROM schema_version WHERE key = 'schema_version'"
    ).fetchone()
    if row is None:
        return 0
    return int(row[0])


def _write_version(conn: sqlite3.Connection, version: int) -> None:
    """Set the schema_version row to ``version`` (upsert)."""
    conn.execute(
        "INSERT OR REPLACE INTO schema_version (key, version) VALUES (?, ?)",
        ("schema_version", version),
    )
