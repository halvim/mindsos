"""
Phase 19 sessions-table DDL tests per PB-10 + minor locks.

Verifies:
* 5-column shape (PB-10 — no stored expires_at).
* PRIMARY KEY on session_id.
* UNIQUE on token_hash.
* FK on user_id → users(user_id) with ON DELETE CASCADE.
* idx_sessions_user_id index exists.
* foreign_keys=ON pragma is set (from open_db).
"""

from __future__ import annotations

import sqlite3

import pytest


class TestColumnShape:
    def test_five_columns(self, tmp_server_db) -> None:
        rows = tmp_server_db.execute("PRAGMA table_info(sessions)").fetchall()
        names = [row[1] for row in rows]
        assert names == [
            "session_id",
            "user_id",
            "token_hash",
            "created_at",
            "last_seen_at",
        ]

    def test_no_expires_at_column(self, tmp_server_db) -> None:
        """PB-10 / ADR-0004 §am1: expires_at is computed, not stored."""
        rows = tmp_server_db.execute("PRAGMA table_info(sessions)").fetchall()
        names = [row[1] for row in rows]
        assert "expires_at" not in names

    def test_no_source_column(self, tmp_server_db) -> None:
        """PB-3 / ADR-0005 §am1: source field deferred to HTTP daemon."""
        rows = tmp_server_db.execute("PRAGMA table_info(sessions)").fetchall()
        names = [row[1] for row in rows]
        assert "source" not in names


class TestPrimaryKey:
    def test_session_id_is_primary_key(self, tmp_server_db) -> None:
        rows = tmp_server_db.execute("PRAGMA table_info(sessions)").fetchall()
        pk_cols = [row[1] for row in rows if row[5] == 1]
        assert pk_cols == ["session_id"]


class TestUniqueTokenHash:
    def test_duplicate_token_hash_rejected(self, tmp_server_db) -> None:
        ts = "2026-05-21T00:00:00.000Z"
        # Pre-seed users to satisfy FK.
        tmp_server_db.execute(
            "INSERT INTO users (user_id, password_hash, actor_role, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("alice", "$argon2id$dummy", "user", ts),
        )
        tmp_server_db.execute(
            "INSERT INTO users (user_id, password_hash, actor_role, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("bob", "$argon2id$dummy", "user", ts),
        )
        tmp_server_db.execute(
            "INSERT INTO sessions "
            "(session_id, user_id, token_hash, created_at, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("s1", "alice", "deadbeef", ts, ts),
        )
        with pytest.raises(sqlite3.IntegrityError):
            tmp_server_db.execute(
                "INSERT INTO sessions "
                "(session_id, user_id, token_hash, created_at, last_seen_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ("s2", "bob", "deadbeef", ts, ts),
            )


class TestForeignKeyCascade:
    """PB-10 final lock: sessions.user_id REFERENCES users(user_id)
    ON DELETE CASCADE. Phase 22 hard_delete_user gets automatic
    session cleanup."""

    def test_delete_user_cascades_sessions(self, tmp_server_db) -> None:
        ts = "2026-05-21T00:00:00.000Z"
        tmp_server_db.execute(
            "INSERT INTO users (user_id, password_hash, actor_role, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("alice", "$argon2id$dummy", "user", ts),
        )
        tmp_server_db.execute(
            "INSERT INTO sessions "
            "(session_id, user_id, token_hash, created_at, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("s1", "alice", "h1", ts, ts),
        )
        tmp_server_db.execute(
            "INSERT INTO sessions "
            "(session_id, user_id, token_hash, created_at, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("s2", "alice", "h2", ts, ts),
        )
        tmp_server_db.commit()

        tmp_server_db.execute("DELETE FROM users WHERE user_id = 'alice'")
        tmp_server_db.commit()

        rows = tmp_server_db.execute(
            "SELECT session_id FROM sessions WHERE user_id = 'alice'"
        ).fetchall()
        assert rows == []

    def test_fk_orphan_insert_rejected(self, tmp_server_db) -> None:
        """Inserting a sessions row whose user_id does not exist in
        users must raise IntegrityError (FK enforced)."""
        ts = "2026-05-21T00:00:00.000Z"
        with pytest.raises(sqlite3.IntegrityError):
            tmp_server_db.execute(
                "INSERT INTO sessions "
                "(session_id, user_id, token_hash, created_at, last_seen_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ("s1", "ghost", "h", ts, ts),
            )


class TestIndex:
    def test_idx_sessions_user_id_exists(self, tmp_server_db) -> None:
        rows = tmp_server_db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='index' AND name='idx_sessions_user_id'"
        ).fetchall()
        assert len(rows) == 1
