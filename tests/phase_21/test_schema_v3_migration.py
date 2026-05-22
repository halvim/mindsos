"""
Phase 21 schema v2→v3 migration tests.

Verifies that ``_SCHEMA_VERSION`` bumps to 3, that ``idx_audit_target``
exists post-migrate, and that v2→v3 is idempotent (re-running
init_or_migrate on a v3 DB does not error or duplicate).

Also verifies PB-19 intentional duplication: ``idx_audit_target``
appears in both ``_DDL_AUDIT_INDEXES`` (for fresh v0→v1 installs) AND
the v2→v3 migration block (for existing v2 installs).

Per ADR-0013 §am2 + Phase 21 PB-7 + PB-19.
"""

from __future__ import annotations

import sqlite3

from mindsos_server._db import open_db
from mindsos_server._schema import (
    _DDL_AUDIT_INDEXES,
    _SCHEMA_VERSION,
    init_or_migrate,
)


class TestSchemaVersion:
    def test_schema_version_constant_is_3(self) -> None:
        assert _SCHEMA_VERSION == 3

    def test_fresh_install_lands_at_v3(self, tmp_server_db_path) -> None:
        with open_db(tmp_server_db_path) as conn:
            init_or_migrate(conn)
            row = conn.execute(
                "SELECT version FROM schema_version WHERE key = ?",
                ("schema_version",),
            ).fetchone()
            assert int(row[0]) == 3


class TestIdxAuditTarget:
    def test_idx_audit_target_exists_after_migrate(
        self, tmp_server_db
    ) -> None:
        rows = tmp_server_db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'index' AND name = 'idx_audit_target'"
        ).fetchall()
        assert len(rows) == 1

    def test_all_four_audit_indexes_present(
        self, tmp_server_db
    ) -> None:
        rows = tmp_server_db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'index' AND tbl_name = 'audit' "
            "AND name LIKE 'idx_audit_%'"
        ).fetchall()
        names = {r[0] for r in rows}
        assert names == {
            "idx_audit_ts",
            "idx_audit_event",
            "idx_audit_actor",
            "idx_audit_target",
        }

    def test_idx_audit_target_in_ddl_list(self) -> None:
        """PB-19 — idx_audit_target appears in _DDL_AUDIT_INDEXES for
        fresh-install v0→v1 path."""
        target_in_list = any(
            "idx_audit_target" in ddl for ddl in _DDL_AUDIT_INDEXES
        )
        assert target_in_list, (
            "PB-19 intentional duplication: idx_audit_target must be "
            "in both _DDL_AUDIT_INDEXES AND the v2→v3 migration block"
        )


class TestIdempotency:
    def test_double_migrate_no_error(self, tmp_server_db_path) -> None:
        with open_db(tmp_server_db_path) as conn:
            init_or_migrate(conn)
            # Second call should be a no-op (current >= each version
            # branch, so no DDL runs).
            init_or_migrate(conn)
            row = conn.execute(
                "SELECT version FROM schema_version WHERE key = ?",
                ("schema_version",),
            ).fetchone()
            assert int(row[0]) == 3

    def test_index_creation_idempotent(
        self, tmp_server_db
    ) -> None:
        # Run CREATE INDEX IF NOT EXISTS twice — second run is no-op.
        tmp_server_db.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_target ON audit(target_user)"
        )
        # No error; index still present.
        rows = tmp_server_db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'index' AND name = 'idx_audit_target'"
        ).fetchall()
        assert len(rows) == 1


class TestMigrationFromV2:
    def test_v2_db_migrates_forward(self, tmp_server_db_path) -> None:
        """
        Simulate an existing v2 DB (Phase 19 schema with NO
        idx_audit_target). Initialize manually at v2, then run
        init_or_migrate and verify it lands at v3 with the new index.
        """
        # Create a v2-only DB by running migrate up to v2, then
        # manually rolling _SCHEMA_VERSION back to 2 and dropping
        # the target index so it looks like a pre-Phase-21 install.
        with open_db(tmp_server_db_path) as conn:
            init_or_migrate(conn)
            conn.execute("DROP INDEX IF EXISTS idx_audit_target")
            conn.execute(
                "UPDATE schema_version SET version = 2 WHERE key = ?",
                ("schema_version",),
            )
            conn.commit()

        # Now reopen + migrate. Should go v2→v3, recreate the index.
        with open_db(tmp_server_db_path) as conn:
            init_or_migrate(conn)
            row = conn.execute(
                "SELECT version FROM schema_version WHERE key = ?",
                ("schema_version",),
            ).fetchone()
            assert int(row[0]) == 3

            idx_rows = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'index' AND name = 'idx_audit_target'"
            ).fetchall()
            assert len(idx_rows) == 1
