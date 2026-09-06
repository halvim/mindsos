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
#: target_user = ?`` a first-class query shape per ADR-0013 §am2);
#: Phase 24 = 4 (adds ``releases`` + ``pending_mutations`` tables per
#: ADR-0114 §1+§2+§am3 for admin-direct ATOM promotion + release
#: lifecycle; CHECK constraints enforce v1 narrow scope —
#: ``mutation_type IN ('PROMOTION')`` + ``status IN ('SHIPPED',
#: 'FAILED')``). ADR-0210 slice 2 = 5 (adds ``llm_config`` — one row per
#: user holding that user's vendor id, credential level, mode and a
#: credential resolver SPEC). ⚠ **The first bump that is not a numbered
#: phase**: ``core_version`` stays ``phase50`` per CR decision 12, so a
#: reader who expects version-to-phase parity here will not find it.
_SCHEMA_VERSION: int = 5


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
# DDL — schema v4 (Phase 24) — ADR-0114 + §am3
# ---------------------------------------------------------------------------

#: ``releases`` table per ADR-0114 §2 + §am3.
#:
#: Single SQLite table recording release-ship lifecycle records.
#: ``status`` CHECK constraint enforces v1 narrow scope (``SHIPPED`` +
#: ``FAILED`` only per Phase 24 design log PB-10(a); v2 quorum-approve
#: lifecycle states extend via forward-only migration).
#:
#: Columns:
#:
#: * ``release_id`` — INTEGER PK AUTOINCREMENT. Monotonic non-reused
#:   per ADR-0114 §Rationale. Referenced by
#:   ``pending_mutations.shipped_in_release`` +
#:   ``releases.parent_release_id`` + ``manifest_json.parent_release_
#:   id`` cross-references.
#: * ``parent_release_id`` — INTEGER NULL FK to releases. Populated at
#:   SHIPPED by ``SELECT MAX(release_id) FROM releases WHERE status =
#:   'SHIPPED'`` immediately before INSERT (Phase 24 design log PB-
#:   17(a) — full table shape at introducing phase). FAILED rows do
#:   NOT become parents (no canonical state was committed).
#: * ``proposer_admin_user_id`` — TEXT NOT NULL FK to users. Who
#:   invoked release_update. v1 semantic differs from v2 quorum-
#:   approve; ADR-0114 §Consequences documents.
#: * ``approver_admin_user_ids_json`` — TEXT NULL. Reserved for v2
#:   quorum-approve. Always NULL at v1; column ships at v4 to avoid
#:   later ALTER (ADR-0114 §Consequences).
#: * ``proposed_at`` — TEXT ISO-8601 UTC ms.
#: * ``shipped_at`` — TEXT NULL ISO-8601 UTC ms; populated when
#:   ``status = 'SHIPPED'``.
#: * ``failed_at`` — TEXT NULL ISO-8601 UTC ms; populated when
#:   ``status = 'FAILED'``.
#: * ``manifest_json`` — TEXT NOT NULL. Two shapes (SHIPPED + FAILED)
#:   per ADR-0114 §3 + §am3 (PB-Z7(a) FAILED extension adds
#:   ``failed_release_canonical_node_ids``).
#: * ``audit_event_id`` — INTEGER NOT NULL FK to audit. The
#:   ``EVT_RELEASE_SHIPPED`` or ``EVT_RELEASE_FAILED`` row.
#: * ``status`` — TEXT NOT NULL CHECK (``'SHIPPED'`` | ``'FAILED'``).
#:
#: ``shipped_at`` XOR ``failed_at`` is enforced in code (release_update
#: write logic) + test (``tests/phase_24/test_releases_schema.py``),
#: not at schema level (SQLite multi-column CHECK is messy).
_DDL_RELEASES = """
CREATE TABLE IF NOT EXISTS releases (
    release_id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_release_id             INTEGER NULL,
    proposer_admin_user_id        TEXT NOT NULL,
    approver_admin_user_ids_json  TEXT NULL,
    proposed_at                   TEXT NOT NULL,
    shipped_at                    TEXT NULL,
    failed_at                     TEXT NULL,
    manifest_json                 TEXT NOT NULL,
    audit_event_id                INTEGER NOT NULL,
    status                        TEXT NOT NULL CHECK (status IN ('SHIPPED', 'FAILED')),
    FOREIGN KEY (parent_release_id)      REFERENCES releases (release_id),
    FOREIGN KEY (proposer_admin_user_id) REFERENCES users (user_id),
    FOREIGN KEY (audit_event_id)         REFERENCES audit (id)
)
"""

#: Indexes on releases table per ADR-0114 §2.
_DDL_RELEASES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_releases_status_shipped_at "
    "ON releases (status, shipped_at)",
    "CREATE INDEX IF NOT EXISTS idx_releases_parent "
    "ON releases (parent_release_id)",
]

#: ``pending_mutations`` table per ADR-0114 §1.
#:
#: Tracks per-propose mutations awaiting release ship.
#:
#: Columns:
#:
#: * ``mutation_id`` — INTEGER PK AUTOINCREMENT. Append-order from
#:   AUTOINCREMENT IS the snapshot order per
#:   ``manifest_json.included_mutation_ids`` (ADR-0056 supersession at
#:   Phase 24 ship per PB-Z6(c) + ADR-0114 §am3 clause 5).
#: * ``proposer_admin_user_id`` — TEXT NOT NULL FK to users.
#: * ``source_user_id`` — TEXT NULL. NULL at v1 (admin-direct only;
#:   source-user-Local path defers to P25). Phase 25 populates.
#: * ``proposed_at`` — TEXT ISO-8601 UTC ms.
#: * ``mutation_type`` — TEXT NOT NULL CHECK (``'PROMOTION'`` only at
#:   v1). PIVOT §7.5's ``'EDGE_ADD'`` / ``'EDGE_DEPRECATE'`` extend at
#:   their consumer phase via forward-only ALTER CHECK (Phase 18 PB-28
#:   ``actor_role`` CHECK pattern).
#: * ``payload_json`` — TEXT NOT NULL. Serialized PromotionItem
#:   (NodeSpec + target_role + kind). Source of node_id extraction
#:   for the after-all-roles-clear DELETE template (PB-Z20(a) +
#:   ADR-0114 §am3 clause 3).
#: * ``audit_event_id`` — INTEGER NOT NULL FK to audit. The
#:   ``EVT_PROMOTION_PROPOSED`` row.
#: * ``frozen_user_local_node_id`` — TEXT NULL. v1 always NULL
#:   (no source-user path). Phase 25 populates.
#: * ``shipped_in_release`` — INTEGER NULL FK to releases. NULL while
#:   pending; set at SHIP. The natural pending predicate per PB-26(b)
#:   audit-gate-snapshot pattern.
_DDL_PENDING_MUTATIONS = """
CREATE TABLE IF NOT EXISTS pending_mutations (
    mutation_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    proposer_admin_user_id     TEXT NOT NULL,
    source_user_id             TEXT NULL,
    proposed_at                TEXT NOT NULL,
    mutation_type              TEXT NOT NULL CHECK (mutation_type IN ('PROMOTION')),
    payload_json               TEXT NOT NULL,
    audit_event_id             INTEGER NOT NULL,
    frozen_user_local_node_id  TEXT NULL,
    shipped_in_release         INTEGER NULL,
    FOREIGN KEY (proposer_admin_user_id) REFERENCES users (user_id),
    FOREIGN KEY (audit_event_id)         REFERENCES audit (id),
    FOREIGN KEY (shipped_in_release)     REFERENCES releases (release_id)
)
"""

#: Partial indexes on pending_mutations per ADR-0114 §1.
#:
#: ``idx_pending_mutations_unshipped`` is the hot-path index — supports
#: the PB-26(b) ``WHERE shipped_in_release IS NULL`` audit-gate-
#: snapshot SELECT in O(pending) not O(history).
_DDL_PENDING_MUTATIONS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_pending_mutations_unshipped "
    "ON pending_mutations (shipped_in_release) "
    "WHERE shipped_in_release IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_pending_mutations_by_release "
    "ON pending_mutations (shipped_in_release) "
    "WHERE shipped_in_release IS NOT NULL",
]


# ---------------------------------------------------------------------------
# DDL — schema v5 (ADR-0210 slice 2) — L0 credential custody
# ---------------------------------------------------------------------------

#: ``llm_config`` — one row per user, per ADR-0210 decisions 5, 6 and 7.
#:
#: **What this table holds is a POINTER, never a secret.** Level 1 means the
#: credential is never STORED: it lives in the user's keychain or environment
#: and MindsOS holds it for the duration of one request. What is stored here is
#: the *way to get it* — a resolver spec — which is why the column below is
#: named ``credential_spec_json`` and not anything with "key" in it. A row that
#: ever holds a credential value is a defect, not a configuration.
#:
#: Columns:
#:
#: * ``user_id`` — PK **and** the only access path. One user, one model
#:   configuration; the client is per session (decision 7) and a session has
#:   exactly one user.
#: * ``vendor_id`` — the stored choice resolved at call time through
#:   ``mindsos_llm.adapters`` (decision 3). Deliberately **not** FK'd or
#:   CHECK-constrained against a vendor list: the registry is runtime data and
#:   a DDL constraint would freeze at migration time the very thing decision 3
#:   made late-bound. An unregistered id raises ``UnknownVendor`` loudly at
#:   client construction, which is the designed failure.
#: * ``credential_level`` — 1/2/3 per ADR-0210 §4, recorded because it
#:   determines how reproducible the answer is (decision 6). CHECK-constrained
#:   because the level set is closed by the ADR, unlike the vendor set.
#: * ``mode`` — live / capture / replay, stamped on every answer (decision 5).
#:   "A mode chosen in code is a mode nothing records."
#: * ``credential_kind`` — the registered kind id (``env`` is the one core
#:   ships). **This is the discriminator L0 reads**, and it is a column rather
#:   than a JSON field precisely so the boundary is visible in the schema: L0
#:   dispatches on this and opens nothing else.
#: * ``credential_spec_json`` — the kind's OWN fields, a JSON object. **L0
#:   never interprets it.** It is handed to the registered kind, which
#:   validates it when it is set and builds a resolver from it at call time.
#:   Splitting the kind out of the JSON also removes the duplicate-source
#:   problem a ``{"kind": ...}`` key inside the blob would have created.
#: * ``updated_at`` — TEXT ISO-8601 UTC ms per PB-35, as everywhere else.
#:
#: ⚠ **``ON DELETE CASCADE``, and it is the OPPOSITE of ``audit``'s choice.**
#: Audit rows carry no FK because they MUST outlive their subjects (ADR-0013
#: §Consequences). A credential pointer must NOT: it names a place a secret
#: lives, and a hard-deleted user's row surviving would leave that name behind
#: with no one to own it. :func:`mindsos_server.admin.hard_delete_user` deletes
#: only from ``users`` and relies on the cascade, exactly as ``sessions`` does.
#:
#: **No index, deliberately.** The primary key IS the access path — every read
#: and every write is one row by ``user_id``. An index on a covered column is
#: drift, and this file has a comment budget for justifying indexes, not for
#: apologising for them.
_DDL_LLM_CONFIG = """
CREATE TABLE IF NOT EXISTS llm_config (
    user_id               TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    vendor_id             TEXT NOT NULL,
    credential_level      INTEGER NOT NULL CHECK (credential_level IN (1, 2, 3)),
    mode                  TEXT NOT NULL CHECK (mode IN ('live', 'capture', 'replay')),
    credential_kind       TEXT NOT NULL,
    credential_spec_json  TEXT NOT NULL,
    updated_at            TEXT NOT NULL
)
"""


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

    # v3 → v4: ship the Phase 24 ``releases`` + ``pending_mutations``
    # tables per ADR-0114 §1+§2+§am3.
    #
    # DDL ordering matters: ``releases`` ships FIRST because
    # ``pending_mutations.shipped_in_release`` FKs to
    # ``releases.release_id`` (ADR-0114 §4). PRAGMA foreign_keys=ON
    # (set in :func:`mindsos_server._db.open_db`) enforces this on
    # subsequent INSERTs but the CREATE TABLE itself parses the FK
    # syntactically — order matters for cleanliness.
    #
    # No data migration needed — both tables start empty; existing
    # users + audit + sessions rows are untouched.
    if current < 4:
        # Step 1: releases (PK + FK target for pending_mutations).
        conn.execute(_DDL_RELEASES)
        for index_ddl in _DDL_RELEASES_INDEXES:
            conn.execute(index_ddl)
        # Step 2: pending_mutations (FKs releases).
        conn.execute(_DDL_PENDING_MUTATIONS)
        for index_ddl in _DDL_PENDING_MUTATIONS_INDEXES:
            conn.execute(index_ddl)
        _write_version(conn, 4)
        conn.commit()
        current = 4

    # v4 → v5: ship the ADR-0210 slice 2 ``llm_config`` table — L0 credential
    # custody. One row per user: vendor id, credential level, mode, and the
    # credential resolver SPEC (a pointer to where a credential lives, never
    # a credential).
    #
    # No data migration needed — the table starts empty and every existing
    # row in every other table is untouched. **A user with no row here has
    # not configured a model, which is a normal state and not an error**:
    # core acquires no vendor, no credential and no network by shipping this
    # table, which is the same property ADR-0210 asserts everywhere else.
    #
    # ⚠ This is the first bump driven by a SLICE rather than a numbered
    # phase. The ladder is still append-only and still forward-only; only the
    # naming of the reason changed.
    if current < 5:
        conn.execute(_DDL_LLM_CONFIG)
        _write_version(conn, 5)
        conn.commit()
        current = 5

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
