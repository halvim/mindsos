"""
Phase 21 admin_query_audit() happy-path tests.

Verifies basic-success case (admin session, no filters, default limit):
returns ``list[AuditRow]`` of all seeded audit rows in id ASC order
plus the EVT_AUDIT_QUERY row written by this call itself (PB-16i —
included in default reader output, transparency).

Per ADR-0013 §am2 + Phase 21 PB-8 + PB-9 + PB-12 + PB-16.
"""

from __future__ import annotations

from mindsos_server.admin import AuditRow, admin_query_audit
from mindsos_server.audit import EVT_AUDIT_QUERY


class TestHappyPath:
    def test_returns_list_of_audit_rows(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        result = admin_query_audit(tmp_server_db, admin_session)
        assert isinstance(result, list)
        assert all(isinstance(r, AuditRow) for r in result)

    def test_returns_all_seeded_rows_plus_self_audit(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # 8 seeded + 1 self-emitted EVT_AUDIT_QUERY = 9 rows.
        result = admin_query_audit(tmp_server_db, admin_session)
        assert len(result) == 9
        # The 9th row (last in ASC order) is the EVT_AUDIT_QUERY this
        # call emitted (PB-16i — included by default).
        assert result[-1].event == EVT_AUDIT_QUERY

    def test_id_asc_order(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        result = admin_query_audit(tmp_server_db, admin_session)
        ids = [r.id for r in result]
        assert ids == sorted(ids)

    def test_default_limit_is_100(
        self, tmp_server_db, admin_session
    ) -> None:
        # Empty DB except for the self-emitted EVT_AUDIT_QUERY row.
        result = admin_query_audit(tmp_server_db, admin_session)
        # Limit is 100 by default; only 1 row exists.
        assert len(result) == 1
        assert result[0].event == EVT_AUDIT_QUERY

    def test_audit_row_fields_populated(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        result = admin_query_audit(tmp_server_db, admin_session)
        # First row is the seeded EVT_BOOTSTRAP one.
        first = result[0]
        assert isinstance(first.id, int)
        assert first.id == seeded_audit_rows[0]
        assert first.ts == "2026-05-21T00:00:00.000Z"
        assert first.actor == "host"
        assert first.event == "EVT_BOOTSTRAP"
        assert first.target == "admin"
        # Sparse extra (seeded with empty dict).
        assert dict(first.extra) == {}

    def test_extra_json_parsed_to_mapping(
        self, tmp_server_db, admin_session, insert_audit_row
    ) -> None:
        # Insert one row with non-trivial extra; assert it's a dict, not a str.
        insert_audit_row(
            "2026-05-21T00:00:00.000Z",
            actor="alice",
            event="EVT_LOGIN_FAILED",
            extra={"cause": "WRONG_PASSWORD", "attempt": 3},
        )
        result = admin_query_audit(tmp_server_db, admin_session)
        login_failed = [r for r in result if r.event == "EVT_LOGIN_FAILED"]
        assert len(login_failed) == 1
        # PB-9 lock: extra is parsed at read-time, not raw JSON string.
        assert isinstance(login_failed[0].extra, dict)
        assert login_failed[0].extra["cause"] == "WRONG_PASSWORD"
        assert login_failed[0].extra["attempt"] == 3
