"""Schema v4 — releases table assertions (ADR-0114 §2 + §am3)."""

from __future__ import annotations


def test_releases_columns(tmp_server_db):
    """releases has the 10 columns per ADR-0114 §2."""
    cur = tmp_server_db.execute("PRAGMA table_info(releases)")
    cols = {row[1] for row in cur.fetchall()}
    expected = {
        "release_id",
        "parent_release_id",
        "proposer_admin_user_id",
        "approver_admin_user_ids_json",
        "proposed_at",
        "shipped_at",
        "failed_at",
        "manifest_json",
        "audit_event_id",
        "status",
    }
    assert cols == expected, (
        f"releases column drift: got {cols} expected {expected}"
    )


def test_releases_status_check_constraint(seeded_admin):
    """status CHECK constraint = ('SHIPPED', 'FAILED') only at v1 per PB-10(a)."""
    import sqlite3
    # SHIPPED is allowed.
    seeded_admin.execute(
        "INSERT INTO releases "
        "(proposer_admin_user_id, proposed_at, shipped_at, manifest_json, "
        "audit_event_id, status) "
        "VALUES ('admin', '2026-05-22T00:00:00.000Z', "
        "'2026-05-22T00:00:01.000Z', '{}', 1, 'SHIPPED')"
    )
    seeded_admin.commit()
    # PROPOSED is NOT allowed at v1.
    try:
        seeded_admin.execute(
            "INSERT INTO releases "
            "(proposer_admin_user_id, proposed_at, manifest_json, "
            "audit_event_id, status) "
            "VALUES ('admin', '2026-05-22T00:00:00.000Z', '{}', 1, "
            "'PROPOSED')"
        )
        seeded_admin.commit()
        raised = False
    except sqlite3.IntegrityError:
        raised = True
    assert raised, "PROPOSED should violate CHECK constraint at v1"


def test_releases_pk_autoincrement(tmp_server_db):
    """release_id PK is INTEGER PRIMARY KEY AUTOINCREMENT."""
    cur = tmp_server_db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='releases'"
    )
    ddl = cur.fetchone()[0]
    assert "AUTOINCREMENT" in ddl.upper()
    assert "release_id" in ddl
    assert "PRIMARY KEY" in ddl.upper()


def test_releases_indexes_exist(tmp_server_db):
    """idx_releases_status_shipped_at + idx_releases_parent exist."""
    cur = tmp_server_db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND tbl_name='releases'"
    )
    names = {row[0] for row in cur.fetchall()}
    assert "idx_releases_status_shipped_at" in names
    assert "idx_releases_parent" in names


def test_schema_version_is_4(tmp_server_db):
    """_SCHEMA_VERSION bumped to 4 at Phase 24."""
    cur = tmp_server_db.execute(
        "SELECT version FROM schema_version WHERE key='schema_version'"
    )
    row = cur.fetchone()
    assert row[0] == 4


def test_releases_v1_v2_columns_null_at_default(seeded_admin):
    """approver_admin_user_ids_json NULL at v1 per ADR-0114 §2."""
    seeded_admin.execute(
        "INSERT INTO releases "
        "(proposer_admin_user_id, proposed_at, shipped_at, manifest_json, "
        "audit_event_id, status) "
        "VALUES ('admin', '2026-05-22T00:00:00.000Z', "
        "'2026-05-22T00:00:01.000Z', '{}', 1, 'SHIPPED')"
    )
    seeded_admin.commit()
    cur = seeded_admin.execute(
        "SELECT approver_admin_user_ids_json, parent_release_id, failed_at "
        "FROM releases"
    )
    row = cur.fetchone()
    assert row == (None, None, None)
