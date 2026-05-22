"""
Phase 21 filter combination tests.

Verifies that actor / event / target kwargs filter the row set
correctly, that null kwargs skip the WHERE clause (PB-27 sparse
filter), and that filters AND together.

Per ADR-0013 §am2 + Phase 21 PB-2 + PB-20 + PB-27.
"""

from __future__ import annotations

from mindsos_server.admin import admin_query_audit
from mindsos_server.audit import (
    EVT_AUDIT_QUERY,
    EVT_KILL_SESSION,
    EVT_LOGIN,
    EVT_LOGOUT,
    EVT_RESET_ADMIN,
)


class TestActorFilter:
    def test_filter_by_actor(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        result = admin_query_audit(
            tmp_server_db, admin_session, actor="alice"
        )
        # Per the seed: rows 3 (EVT_LOGIN_FAILED), 7 (EVT_LOGIN),
        # 8 (EVT_LOGOUT) have actor='alice'. EVT_AUDIT_QUERY is
        # actor='admin', so excluded.
        assert {r.id for r in result} == {
            seeded_audit_rows[2],
            seeded_audit_rows[6],
            seeded_audit_rows[7],
        }

    def test_actor_none_skips_filter(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # Explicit actor=None should NOT match rows where actor_user IS NULL.
        # (PB-27 — None means "no filter on this column".)
        result = admin_query_audit(
            tmp_server_db, admin_session, actor=None
        )
        # All 8 seeded + 1 EVT_AUDIT_QUERY = 9.
        assert len(result) == 9


class TestEventFilter:
    def test_filter_by_event(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        result = admin_query_audit(
            tmp_server_db, admin_session, event=EVT_LOGIN
        )
        # Seed has 2 EVT_LOGIN rows (ids 2, 7).
        assert {r.id for r in result} == {
            seeded_audit_rows[1],
            seeded_audit_rows[6],
        }

    def test_filter_by_evt_audit_query(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # Self-emitted EVT_AUDIT_QUERY is in default output.
        result = admin_query_audit(
            tmp_server_db, admin_session, event=EVT_AUDIT_QUERY
        )
        # This call writes one EVT_AUDIT_QUERY row.
        assert len(result) == 1
        assert result[0].event == EVT_AUDIT_QUERY


class TestTargetFilter:
    def test_filter_by_target(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        result = admin_query_audit(
            tmp_server_db, admin_session, target="admin"
        )
        # Seed has 3 rows with target='admin': EVT_BOOTSTRAP (1),
        # EVT_RESET_ADMIN (5), EVT_KILL_SESSION (6).
        assert {r.id for r in result} == {
            seeded_audit_rows[0],
            seeded_audit_rows[4],
            seeded_audit_rows[5],
        }


class TestAndCombinations:
    def test_actor_and_event(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # actor='alice' AND event='EVT_LOGIN' → only id 7.
        result = admin_query_audit(
            tmp_server_db, admin_session,
            actor="alice", event=EVT_LOGIN,
        )
        assert {r.id for r in result} == {seeded_audit_rows[6]}

    def test_actor_and_target(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # actor='host' AND target='admin' → EVT_BOOTSTRAP, EVT_RESET_ADMIN,
        # EVT_KILL_SESSION (ids 1, 5, 6).
        result = admin_query_audit(
            tmp_server_db, admin_session,
            actor="host", target="admin",
        )
        assert {r.id for r in result} == {
            seeded_audit_rows[0],
            seeded_audit_rows[4],
            seeded_audit_rows[5],
        }

    def test_all_three_filters_empty_intersection(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # actor='alice' AND event='EVT_LOGIN' AND target='admin' → no row.
        result = admin_query_audit(
            tmp_server_db, admin_session,
            actor="alice", event=EVT_LOGIN, target="admin",
        )
        assert result == []


class TestActorTargetSeparation:
    """
    PB-2(a): actor and target are SEPARATE kwargs, not a collapsed
    'user' filter. A row with actor='admin' and target='alice'
    matches actor='admin' but NOT target='admin'.
    """

    def test_actor_does_not_match_target(
        self, tmp_server_db, admin_session, insert_audit_row
    ) -> None:
        # Insert: actor='admin', target='alice'. Should match
        # actor='admin' but NOT target='admin'.
        insert_audit_row(
            "2026-05-21T00:00:00.000Z",
            actor="admin", event="EVT_LOGIN_FAILED", target="alice",
        )
        as_actor = admin_query_audit(
            tmp_server_db, admin_session, actor="admin",
        )
        # Should include the EVT_LOGIN_FAILED + the self-EVT_AUDIT_QUERY.
        as_actor_events = {r.event for r in as_actor}
        assert "EVT_LOGIN_FAILED" in as_actor_events

        # Re-query with target='admin' (different actor than above).
        as_target = admin_query_audit(
            tmp_server_db, admin_session, target="admin",
        )
        # No row has target='admin' in this scenario.
        as_target_events = {r.event for r in as_target}
        assert "EVT_LOGIN_FAILED" not in as_target_events
