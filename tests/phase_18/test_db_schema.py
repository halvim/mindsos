"""
Tests for ``mindsos_server._db`` + ``mindsos_server._schema`` — Phase 18
PB-2 + PB-11 + PB-19 + PB-28.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mindsos_server._db import open_db
from mindsos_server._schema import _SCHEMA_VERSION, init_or_migrate


class TestSchemaVersion:
    """``_SCHEMA_VERSION`` current baseline — Phase 18 shipped v1
    (PB-2 / PB-11); Phase 19 bumped to v2 (PB-10 sessions). Bumps are
    expected at most-phases; per ``feedback_phase_baseline_literal_audit.md``
    this assertion mirrors the current literal in
    :mod:`mindsos_server._schema`. Each new schema phase updates this
    test alongside the bump."""

    def test_schema_version_baseline(self) -> None:
        # Phase 19: bumped 1 → 2 (sessions table addition).
        assert _SCHEMA_VERSION == 2


class TestWalPragma:
    """PB-19 — every open_db connection sets WAL + foreign_keys + busy_timeout."""

    def test_journal_mode_is_wal(self, tmp_path: Path) -> None:
        db_path = tmp_path / "server.db"
        with open_db(db_path) as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode.lower() == "wal"

    def test_foreign_keys_on(self, tmp_path: Path) -> None:
        db_path = tmp_path / "server.db"
        with open_db(db_path) as conn:
            fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
            assert fk == 1

    def test_busy_timeout_5000(self, tmp_path: Path) -> None:
        db_path = tmp_path / "server.db"
        with open_db(db_path) as conn:
            timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
            assert timeout == 5000


class TestInitOrMigrateIdempotent:
    """PB-2 — init_or_migrate is idempotent. Returns the current
    ``_SCHEMA_VERSION`` literal which bumps at most-phases (see
    :class:`TestSchemaVersion`)."""

    def test_first_call_ships_current(self, tmp_path: Path) -> None:
        db_path = tmp_path / "server.db"
        with open_db(db_path) as conn:
            version = init_or_migrate(conn)
            assert version == _SCHEMA_VERSION

    def test_second_call_no_op(self, tmp_path: Path) -> None:
        db_path = tmp_path / "server.db"
        with open_db(db_path) as conn:
            init_or_migrate(conn)
            version = init_or_migrate(conn)
            assert version == _SCHEMA_VERSION


class TestSchemaTables:
    """PB-11 — Phase 18 shipped users + audit + schema_version (v1);
    Phase 19 bumped to v2 with sessions (PB-10). Each phase's table set
    is asserted against the current schema baseline."""

    def test_users_table_exists(self, tmp_server_db) -> None:
        rows = tmp_server_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchall()
        assert len(rows) == 1

    def test_audit_table_exists(self, tmp_server_db) -> None:
        rows = tmp_server_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit'"
        ).fetchall()
        assert len(rows) == 1

    def test_schema_version_table_exists(self, tmp_server_db) -> None:
        rows = tmp_server_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchall()
        assert len(rows) == 1

    def test_sessions_table_exists_at_v2(self, tmp_server_db) -> None:
        """Sessions ships at Phase 19 (v2) per PB-10 / ADR-0004 §am1.
        Phase 18 originally asserted absence; Phase 19 flipped to presence."""
        rows = tmp_server_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        ).fetchall()
        assert len(rows) == 1

    def test_schema_version_row(self, tmp_server_db) -> None:
        row = tmp_server_db.execute(
            "SELECT version FROM schema_version WHERE key='schema_version'"
        ).fetchone()
        assert row is not None
        assert row[0] == _SCHEMA_VERSION


class TestActorRoleCheckConstraint:
    """PB-28 — actor_role CHECK IN ('user', 'admin') enforced at DB."""

    def test_invalid_actor_role_rejected(self, tmp_server_db) -> None:
        with pytest.raises(sqlite3.IntegrityError):
            tmp_server_db.execute(
                "INSERT INTO users (user_id, password_hash, actor_role, created_at) "
                "VALUES (?, ?, ?, ?)",
                ("alice", "$argon2id$fake", "superadmin", "2026-05-21T00:00:00.000Z"),
            )

    def test_valid_user_role_accepted(self, tmp_server_db) -> None:
        tmp_server_db.execute(
            "INSERT INTO users (user_id, password_hash, actor_role, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("alice", "$argon2id$fake", "user", "2026-05-21T00:00:00.000Z"),
        )

    def test_valid_admin_role_accepted(self, tmp_server_db) -> None:
        tmp_server_db.execute(
            "INSERT INTO users (user_id, password_hash, actor_role, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("alice", "$argon2id$fake", "admin", "2026-05-21T00:00:00.000Z"),
        )


class TestDisabledCheckConstraint:
    """disabled CHECK IN (0, 1) enforced at DB."""

    def test_invalid_disabled_rejected(self, tmp_server_db) -> None:
        with pytest.raises(sqlite3.IntegrityError):
            tmp_server_db.execute(
                "INSERT INTO users (user_id, password_hash, actor_role, disabled, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ("alice", "$argon2id$fake", "user", 2, "2026-05-21T00:00:00.000Z"),
            )


class TestUserIdPrimaryKey:
    """PB-16 — user_id is the PRIMARY KEY; UNIQUE violations on duplicate."""

    def test_duplicate_user_id_rejected(self, tmp_server_db) -> None:
        tmp_server_db.execute(
            "INSERT INTO users (user_id, password_hash, actor_role, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("alice", "$argon2id$fake", "user", "2026-05-21T00:00:00.000Z"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            tmp_server_db.execute(
                "INSERT INTO users (user_id, password_hash, actor_role, created_at) "
                "VALUES (?, ?, ?, ?)",
                ("alice", "$argon2id$fake2", "admin", "2026-05-21T00:00:00.001Z"),
            )
