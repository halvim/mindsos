"""Schema v4 — pending_mutations table assertions (ADR-0114 §1)."""

from __future__ import annotations


def test_pending_mutations_columns(tmp_server_db):
    """pending_mutations has the 9 columns per ADR-0114 §1."""
    cur = tmp_server_db.execute("PRAGMA table_info(pending_mutations)")
    cols = {row[1]: row for row in cur.fetchall()}
    expected = {
        "mutation_id",
        "proposer_admin_user_id",
        "source_user_id",
        "proposed_at",
        "mutation_type",
        "payload_json",
        "audit_event_id",
        "frozen_user_local_node_id",
        "shipped_in_release",
    }
    assert set(cols.keys()) == expected, (
        f"pending_mutations column drift: got {set(cols.keys())} "
        f"expected {expected}"
    )


def test_pending_mutations_pk_is_autoincrement(tmp_server_db):
    """mutation_id PK is INTEGER PRIMARY KEY AUTOINCREMENT per ADR-0114 §1."""
    cur = tmp_server_db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' "
        "AND name='pending_mutations'"
    )
    ddl = cur.fetchone()[0]
    assert "AUTOINCREMENT" in ddl.upper()
    assert "mutation_id" in ddl
    assert "PRIMARY KEY" in ddl.upper()


def test_pending_mutations_mutation_type_check_constraint(seeded_admin):
    """mutation_type CHECK constraint enforces v1 narrow scope."""
    import sqlite3
    # PROMOTION is allowed.
    seeded_admin.execute(
        "INSERT INTO pending_mutations "
        "(proposer_admin_user_id, proposed_at, mutation_type, "
        "payload_json, audit_event_id) "
        "VALUES ('admin', '2026-05-22T00:00:00.000Z', 'PROMOTION', "
        "'{}', 1)"
    )
    seeded_admin.commit()
    # EDGE_ADD is NOT allowed at v1.
    try:
        seeded_admin.execute(
            "INSERT INTO pending_mutations "
            "(proposer_admin_user_id, proposed_at, mutation_type, "
            "payload_json, audit_event_id) "
            "VALUES ('admin', '2026-05-22T00:00:00.000Z', 'EDGE_ADD', "
            "'{}', 1)"
        )
        seeded_admin.commit()
        raised = False
    except sqlite3.IntegrityError:
        raised = True
    assert raised, "EDGE_ADD should violate CHECK constraint at v1"


def test_pending_mutations_partial_index_unshipped_exists(tmp_server_db):
    """idx_pending_mutations_unshipped exists per ADR-0114 §1."""
    cur = tmp_server_db.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' "
        "AND name='idx_pending_mutations_unshipped'"
    )
    row = cur.fetchone()
    assert row is not None
    # Partial-index predicate present.
    assert "shipped_in_release IS NULL" in row[0]


def test_pending_mutations_by_release_index_exists(tmp_server_db):
    """idx_pending_mutations_by_release exists per ADR-0114 §1."""
    cur = tmp_server_db.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' "
        "AND name='idx_pending_mutations_by_release'"
    )
    assert cur.fetchone() is not None


def test_pending_mutations_v1_source_user_id_is_null_default(seeded_admin):
    """source_user_id + frozen_user_local_node_id default NULL per ADR-0114 §1.

    Both columns ship at v4 for the Phase 25 source-user path; at v1
    they're always NULL (admin-direct ATOM only per PB-11(a)).
    """
    # Audit row id=1 was inserted by _insert_first_admin (EVT_BOOTSTRAP).
    seeded_admin.execute(
        "INSERT INTO pending_mutations "
        "(proposer_admin_user_id, proposed_at, mutation_type, "
        "payload_json, audit_event_id) "
        "VALUES ('admin', '2026-05-22T00:00:00.000Z', 'PROMOTION', "
        "'{}', 1)"
    )
    seeded_admin.commit()
    cur = seeded_admin.execute(
        "SELECT source_user_id, frozen_user_local_node_id, shipped_in_release "
        "FROM pending_mutations"
    )
    row = cur.fetchone()
    assert row == (None, None, None)
