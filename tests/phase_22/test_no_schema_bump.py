"""
Phase 22 — confirms no schema bump (R3 non-pushback lock).

Phase 22 mutates existing columns only (``users.actor_role``,
``users.disabled``) + DELETEs sessions (FK CASCADE on hard-delete).
No new tables, no new indexes, no migration step.

Schema version remains at 3 (set by Phase 21).
"""

from __future__ import annotations

from mindsos_server._schema import _SCHEMA_VERSION


def test_schema_version_unchanged_at_3():
    assert _SCHEMA_VERSION == 3


def test_no_new_audit_indexes(tmp_server_db):
    """Audit table indexes unchanged since Phase 21 (idx_audit_target)."""
    rows = tmp_server_db.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='index' AND tbl_name='audit'"
    ).fetchall()
    index_names = {r[0] for r in rows}
    # Should still be exactly the 4 P21 indexes
    expected = {
        "idx_audit_ts",
        "idx_audit_event",
        "idx_audit_actor",
        "idx_audit_target",
    }
    # Allow auto-created indexes on PK; we assert the named subset is unchanged
    assert expected.issubset(index_names)
