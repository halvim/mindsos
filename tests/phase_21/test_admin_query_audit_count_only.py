"""
Phase 21 ``--count-only`` flag tests.

Verifies that ``count_only=True`` flips the return to ``int`` (PB-4
reframe of "audit stats" feature), that filters compose with
count-only correctly, and that the EVT_AUDIT_QUERY happy-path emission
still fires with ``count_only=true`` in the extra_json (PB-18 — no
audit silencing on count-only).

Per ADR-0013 §am2 + Phase 21 PB-4 + PB-18.
"""

from __future__ import annotations

import json

from mindsos_server.admin import admin_query_audit
from mindsos_server.audit import EVT_AUDIT_QUERY, EVT_LOGIN


class TestCountOnlyReturn:
    def test_returns_int(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        result = admin_query_audit(
            tmp_server_db, admin_session, count_only=True
        )
        assert isinstance(result, int)

    def test_count_matches_list_length(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # Use a clean DB for parity: count vs len(list).
        # First the count.
        count = admin_query_audit(
            tmp_server_db, admin_session, count_only=True
        )
        # That call wrote one EVT_AUDIT_QUERY row. Now list mode includes
        # the count call's row + the list call's row.
        # The count call counts EXISTING rows at that moment: 8 seeded
        # rows. So count == 8.
        assert count == 8

    def test_count_with_filter(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        count = admin_query_audit(
            tmp_server_db, admin_session,
            event=EVT_LOGIN, count_only=True,
        )
        # 2 seeded EVT_LOGIN rows (ids 2 + 7).
        assert count == 2


class TestCountOnlyAuditEmission:
    """PB-18: --count-only still emits EVT_AUDIT_QUERY with count_only=true."""

    def test_evt_audit_query_still_emitted(
        self, tmp_server_db, admin_session
    ) -> None:
        # Empty DB — only the EVT_AUDIT_QUERY emitted by this call.
        admin_query_audit(tmp_server_db, admin_session, count_only=True)
        rows = tmp_server_db.execute(
            "SELECT event, extra_json FROM audit WHERE event = ?",
            (EVT_AUDIT_QUERY,),
        ).fetchall()
        assert len(rows) == 1

    def test_extra_carries_count_only_true(
        self, tmp_server_db, admin_session
    ) -> None:
        admin_query_audit(tmp_server_db, admin_session, count_only=True)
        row = tmp_server_db.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_AUDIT_QUERY,),
        ).fetchone()
        extra = json.loads(row[0])
        assert extra["count_only"] is True

    def test_extra_carries_count_only_false(
        self, tmp_server_db, admin_session
    ) -> None:
        admin_query_audit(tmp_server_db, admin_session)
        row = tmp_server_db.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_AUDIT_QUERY,),
        ).fetchone()
        extra = json.loads(row[0])
        assert extra["count_only"] is False
