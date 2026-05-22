"""
Phase 21 EVT_AUDIT_QUERY emission tests.

Verifies that the happy-path audit row is emitted per call (PB-16),
that the extra_json carries the sparse filters snapshot + count +
count_only flag (PB-17), and that EVT_AUDIT_QUERY rows are included
in default reader output (PB-16i).

Per ADR-0013 §am2 + Phase 21 PB-16 + PB-16i + PB-17.
"""

from __future__ import annotations

import json

from mindsos_server.admin import admin_query_audit
from mindsos_server.audit import (
    ALL_AUDIT_EVENTS,
    EVT_AUDIT_QUERY,
    EVT_LOGIN,
)


class TestConstantExists:
    """PB-16 — EVT_AUDIT_QUERY constant added to audit.py."""

    def test_constant_value(self) -> None:
        assert EVT_AUDIT_QUERY == "EVT_AUDIT_QUERY"

    def test_constant_in_all_audit_events(self) -> None:
        assert EVT_AUDIT_QUERY in ALL_AUDIT_EVENTS


class TestPerCallEmission:
    def test_one_row_per_call(
        self, tmp_server_db, admin_session
    ) -> None:
        admin_query_audit(tmp_server_db, admin_session)
        admin_query_audit(tmp_server_db, admin_session)
        admin_query_audit(tmp_server_db, admin_session)
        count = tmp_server_db.execute(
            "SELECT COUNT(*) FROM audit WHERE event = ?",
            (EVT_AUDIT_QUERY,),
        ).fetchone()[0]
        assert count == 3

    def test_emission_after_returning_rows(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # The EVT_AUDIT_QUERY row has the highest id (emitted last).
        # First call returns 8 seeded + 1 EVT_AUDIT_QUERY = 9 rows.
        result = admin_query_audit(tmp_server_db, admin_session)
        assert len(result) == 9
        assert result[-1].event == EVT_AUDIT_QUERY
        assert result[-1].id == max(r.id for r in result)


class TestFiltersSnapshot:
    """PB-17 — extra.filters is a sparse snapshot of non-None kwargs."""

    def test_all_none_filters_recorded_as_only_limit(
        self, tmp_server_db, admin_session
    ) -> None:
        admin_query_audit(tmp_server_db, admin_session)
        row = tmp_server_db.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_AUDIT_QUERY,),
        ).fetchone()
        extra = json.loads(row[0])
        # Sparse: only the always-recorded limit shows up; all
        # None-valued kwargs omitted.
        assert extra["filters"] == {"limit": 100}

    def test_filters_record_non_null_kwargs(
        self, tmp_server_db, admin_session
    ) -> None:
        admin_query_audit(
            tmp_server_db, admin_session,
            actor="alice", event=EVT_LOGIN,
        )
        row = tmp_server_db.execute(
            "SELECT extra_json FROM audit WHERE event = ? "
            "ORDER BY id DESC LIMIT 1",
            (EVT_AUDIT_QUERY,),
        ).fetchone()
        extra = json.loads(row[0])
        assert extra["filters"]["actor"] == "alice"
        assert extra["filters"]["event"] == EVT_LOGIN
        # since/until/target/after_id all None → omitted.
        assert "since" not in extra["filters"]
        assert "until" not in extra["filters"]
        assert "target" not in extra["filters"]
        assert "after_id" not in extra["filters"]

    def test_count_recorded(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # No filter → all 8 seeded rows + 0 prior EVT_AUDIT_QUERY = 8.
        admin_query_audit(tmp_server_db, admin_session)
        row = tmp_server_db.execute(
            "SELECT extra_json FROM audit WHERE event = ? "
            "ORDER BY id DESC LIMIT 1",
            (EVT_AUDIT_QUERY,),
        ).fetchone()
        extra = json.loads(row[0])
        # count is the result count BEFORE the EVT_AUDIT_QUERY row was
        # written (the row writes after the SELECT happens).
        assert extra["count"] == 8

    def test_actor_field_is_session_user_id(
        self, tmp_server_db, admin_session
    ) -> None:
        admin_query_audit(tmp_server_db, admin_session)
        row = tmp_server_db.execute(
            "SELECT actor_user, target_user FROM audit WHERE event = ?",
            (EVT_AUDIT_QUERY,),
        ).fetchone()
        # actor=session.user_id; target=None per implementation.
        assert row[0] == "admin"
        assert row[1] is None


class TestIncludedInDefaultOutput:
    """PB-16i — EVT_AUDIT_QUERY rows visible in default reader output."""

    def test_evt_audit_query_visible(
        self, tmp_server_db, admin_session
    ) -> None:
        # Empty DB except for this call's emission.
        result = admin_query_audit(tmp_server_db, admin_session)
        events = [r.event for r in result]
        assert EVT_AUDIT_QUERY in events
