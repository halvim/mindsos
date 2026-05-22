"""
Phase 22 R1 PB-11 + R2 PB-14 + PB-17 + PB-18 — hard_delete_user.

Covers:
* Happy path: user row deleted; FK CASCADE clears sessions.
* Per-row EVT_KILL_SESSION + summary EVT_HARD_DELETE_USER (audit-before-state).
* LastAdminError on sole-active-admin target.
* Disabled admin target: no sole-admin check.
* Audit rows OUTLIVE the user row (ADR-0013 §Consequences).
* UserNotFoundError on missing.
"""

from __future__ import annotations

import json

import pytest

from mindsos_server.admin import HardDeleteUserResult, hard_delete_user
from mindsos_server.audit import (
    EVT_HARD_DELETE_USER,
    EVT_KILL_SESSION,
)
from mindsos_server.errors import LastAdminError, UserNotFoundError


class TestHappyPath:
    def test_returns_result(self, seeded_user, admin_session):
        result = hard_delete_user(
            seeded_user, admin_session, target_user_id="alice"
        )
        assert isinstance(result, HardDeleteUserResult)
        assert result.target_user_id == "alice"
        assert result.prior_role == "user"
        assert result.was_disabled is False
        assert result.sessions_killed == 0

    def test_user_row_deleted(self, seeded_user, admin_session):
        hard_delete_user(seeded_user, admin_session, target_user_id="alice")
        row = seeded_user.execute(
            "SELECT user_id FROM users WHERE user_id = 'alice'"
        ).fetchone()
        assert row is None


class TestCascadeOnSessions:
    def test_sessions_deleted_via_cascade(
        self, seeded_user_with_sessions, admin_session
    ):
        conn, session_ids = seeded_user_with_sessions
        hard_delete_user(conn, admin_session, target_user_id="alice")
        rows = conn.execute(
            "SELECT session_id FROM sessions WHERE user_id = 'alice'"
        ).fetchall()
        assert rows == []

    def test_evt_kill_session_per_row(
        self, seeded_user_with_sessions, admin_session
    ):
        conn, session_ids = seeded_user_with_sessions
        hard_delete_user(conn, admin_session, target_user_id="alice")
        rows = conn.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_KILL_SESSION,),
        ).fetchall()
        assert len(rows) == len(session_ids)
        extras = [json.loads(r[0]) for r in rows]
        assert all(e["context"] == "hard_delete_user" for e in extras)
        recorded = sorted(e["session_id"] for e in extras)
        assert recorded == sorted(session_ids)

    def test_summary_audit_row_payload(
        self, seeded_user_with_sessions, admin_session
    ):
        conn, session_ids = seeded_user_with_sessions
        hard_delete_user(conn, admin_session, target_user_id="alice")
        rows = conn.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_HARD_DELETE_USER,),
        ).fetchall()
        assert len(rows) == 1
        extra = json.loads(rows[0][0])
        assert extra == {
            "prior_role": "user",
            "was_disabled": False,
            "sessions_killed": len(session_ids),
        }


class TestSoleAdmin:
    def test_active_sole_admin_raises(self, seeded_admin, admin_session):
        with pytest.raises(LastAdminError):
            hard_delete_user(
                seeded_admin, admin_session, target_user_id="admin"
            )

    def test_disabled_admin_no_check(
        self, seeded_disabled_admin_extra, admin_session
    ):
        # 'admin' is active sole admin; 'admin2' is disabled admin.
        # Deleting admin2 should NOT fire LastAdminError (the helper
        # gates on disabled=0 admins only).
        result = hard_delete_user(
            seeded_disabled_admin_extra,
            admin_session,
            target_user_id="admin2",
        )
        assert result.was_disabled is True
        assert result.prior_role == "admin"


class TestAuditOutlivesUser:
    def test_audit_rows_persist_after_delete(
        self, seeded_user, admin_session
    ):
        hard_delete_user(seeded_user, admin_session, target_user_id="alice")
        # User row is gone (CASCADE-style; no audit FK)
        user_row = seeded_user.execute(
            "SELECT user_id FROM users WHERE user_id = 'alice'"
        ).fetchone()
        assert user_row is None
        # But audit rows with target_user='alice' persist
        audit_rows = seeded_user.execute(
            "SELECT id, event FROM audit WHERE target_user = 'alice'"
        ).fetchall()
        assert any(r[1] == EVT_HARD_DELETE_USER for r in audit_rows)


class TestUserNotFound:
    def test_raises(self, seeded_admin, admin_session):
        with pytest.raises(UserNotFoundError):
            hard_delete_user(
                seeded_admin, admin_session, target_user_id="nobody"
            )
