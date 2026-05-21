"""
SQLite schema + forward-only migration framework for ``server.db``.

Phase 18 ships **schema v1** with two tables (``users`` + ``audit``) +
the ``schema_version`` tracking row. Phase 19 will ship v2 adding
``sessions``; Phase 21 reads the ``audit`` table shipped here (no
schema change at 21 per Phase 18 PB-11).

Migration framework per Phase 18 PB-2:

* Forward-only DDL.
* One ``schema_version`` row tracks the current version integer.
* :func:`init_or_migrate` is idempotent: safe to call on a fresh DB
  (creates everything) or an already-migrated DB (no-op). Future
  migrations (v1 → v2 at Phase 19) append a new DDL block + bump the
  ``_SCHEMA_VERSION`` constant + add an upgrade step.

No external migration framework (no Alembic, no yoyo) per PB-2: the
three-table v1 schema does not justify the dep + tooling overhead.

Phase 18 PB-19 — every connection that touches ``server.db`` MUST be
opened via :func:`mindsos_server._db.open_db` which sets the WAL +
foreign_keys + busy_timeout pragmas. :func:`init_or_migrate` assumes
those pragmas are in effect on the passed connection.
"""

from __future__ import annotations

import sqlite3

#: Current schema version. Bump in lockstep with adding a new migration
#: step in :func:`init_or_migrate`. Phase 18 = 1; Phase 19 will bump to
#: 2 to add the ``sessions`` table.
_SCHEMA_VERSION: int = 1


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
#: Phase 21 will likely add more indexes as query patterns crystallize;
#: Phase 18 ships the obvious ones (by time, by event, by actor).
_DDL_AUDIT_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit(ts)",
    "CREATE INDEX IF NOT EXISTS idx_audit_event ON audit(event)",
    "CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit(actor_user)",
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

    # Future: v1 → v2 (Phase 19, add sessions table) goes here.
    # if current < 2:
    #     conn.execute(_DDL_SESSIONS)
    #     _write_version(conn, 2)
    #     conn.commit()
    #     current = 2

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
