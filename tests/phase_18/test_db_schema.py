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
    """_SCHEMA_VERSION = 1 per PB-2 / PB-11."""

    def test_schema_version_is_one(self) -> None:
        assert _SCHEMA_VERSION == 1


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
    """PB-2 — init_or_migrate is idempotent."""

    def test_first_call_ships_v1(self, tmp_path: Path) -> None:
        db_path = tmp_path / "server.db"
        with open_db(db_path) as conn:
            version = init_or_migrate(conn)
            assert version == 1

    def test_second_call_no_op(self, tmp_path: Path) -> None:
        db_path = tmp_path / "server.db"
        with open_db(db_path) as conn:
            init_or_migrate(conn)
            version = init_or_migrate(conn)
            assert version == 1


class TestSchemaTables:
    """PB-11 — v1 ships users + audit + schema_version. No sessions yet (P19)."""

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

    def test_no_sessions_table_at_v1(self, tmp_server_db) -> None:
        """Sessions ships at Phase 19 (v2) per PB-11. Must NOT exist in v1."""
        rows = tmp_server_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        ).fetchall()
        assert len(rows) == 0

    def test_schema_version_row(self, tmp_server_db) -> None:
        row = tmp_server_db.execute(
            "SELECT version FROM schema_version WHERE key='schema_version'"
        ).fetchone()
        assert row is not None
        assert row[0] == 1


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
