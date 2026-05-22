"""
Phase 19 v1 → v2 migration tests per PB-2 + PB-10.

Phase 21 update: assertions generalized against ``_SCHEMA_VERSION``
to end the literal-decay class (B-19-T1 lesson — same dynamic-baseline
pattern as ``TestAll6PkgsAtCurrentPhase``). The file's intent stays
focused on the v1→v2 forward path (the v2 sessions-table addition
is the only thing this phase shipped); the assertions verify the
migrator advances correctly and that v2-and-later state is present.

Verifies:
* ``_SCHEMA_VERSION >= 2`` (sessions table contract holds at v2+).
* ``init_or_migrate`` on a fresh DB returns the current
  ``_SCHEMA_VERSION`` and creates the ``sessions`` table.
* ``init_or_migrate`` on an artificially-rolled-back v1 DB advances
  forward to the current ``_SCHEMA_VERSION`` without touching
  existing rows.
* Idempotency: a second call is a no-op.
* schema_version row reflects ``_SCHEMA_VERSION``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mindsos_server._db import open_db
from mindsos_server._schema import _SCHEMA_VERSION, init_or_migrate


class TestSchemaVersionConstant:
    def test_schema_version_at_least_v2(self) -> None:
        # Phase 19 contract: sessions table exists at v2+; schema can
        # grow forward without invalidating this test.
        assert _SCHEMA_VERSION >= 2


class TestFreshMigration:
    def test_fresh_db_arrives_at_current_version(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "server.db"
        with open_db(db_path) as conn:
            version = init_or_migrate(conn)
            assert version == _SCHEMA_VERSION

    def test_fresh_db_has_sessions_table(self, tmp_path: Path) -> None:
        db_path = tmp_path / "server.db"
        with open_db(db_path) as conn:
            init_or_migrate(conn)
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
            ).fetchall()
            assert len(rows) == 1

    def test_fresh_db_has_users_and_audit_too(self, tmp_path: Path) -> None:
        db_path = tmp_path / "server.db"
        with open_db(db_path) as conn:
            init_or_migrate(conn)
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            assert {"users", "audit", "sessions", "schema_version"}.issubset(tables)


class TestStepwiseMigration:
    """v1 → v2 forward path: simulate a v1 DB (existing P18 install)
    then run init_or_migrate and verify v2 lands without data loss."""

    def test_v1_to_v2_preserves_users(self, tmp_path: Path) -> None:
        db_path = tmp_path / "server.db"

        # Stage a v1 DB: insert users + audit but pin schema_version=1
        # (manually undoing the v2 step).
        with open_db(db_path) as conn:
            init_or_migrate(conn)  # gets to v2
            conn.execute("DROP TABLE sessions")
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (key, version) "
                "VALUES ('schema_version', 1)"
            )
            conn.execute(
                "INSERT INTO users (user_id, password_hash, actor_role, created_at) "
                "VALUES (?, ?, ?, ?)",
                ("preexisting", "$argon2id$dummy", "admin", "2026-05-21T00:00:00.000Z"),
            )
            conn.commit()

        # Re-open and migrate — should advance forward (skipping past
        # v2 to current _SCHEMA_VERSION) + add sessions table + preserve
        # the preexisting users row.
        with open_db(db_path) as conn:
            version = init_or_migrate(conn)
            assert version == _SCHEMA_VERSION
            row = conn.execute(
                "SELECT user_id FROM users WHERE user_id='preexisting'"
            ).fetchone()
            assert row == ("preexisting",)
            # sessions table now exists (v2 step added it; later steps
            # don't drop it).
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
            ).fetchall()
            assert len(rows) == 1


class TestIdempotent:
    def test_second_call_no_op(self, tmp_path: Path) -> None:
        db_path = tmp_path / "server.db"
        with open_db(db_path) as conn:
            init_or_migrate(conn)
            version = init_or_migrate(conn)
            assert version == _SCHEMA_VERSION

    def test_schema_version_row_matches_constant(self, tmp_path: Path) -> None:
        db_path = tmp_path / "server.db"
        with open_db(db_path) as conn:
            init_or_migrate(conn)
            row = conn.execute(
                "SELECT version FROM schema_version WHERE key='schema_version'"
            ).fetchone()
            assert row == (_SCHEMA_VERSION,)
