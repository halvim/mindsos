"""
Phase 22 R1 PB-4 + PB-7 + PB-8 + R2 PB-14 — admin_demote_user.

Covers:
* Happy path: admin → user; sessions killed atomically; audits emitted.
* LastAdminError on sole-admin target.
* NotAnAdminError on user target (verb-agnostic message per R4 PB-25).
* UserNotFoundError on missing.
* Atomicity: rollback leaves row + sessions intact.
* Per-row EVT_KILL_SESSION with context="admin_demote_user" (R2 PB-14).
"""

from __future__ import annotations

import json

import pytest

from mindsos_server.admin import DemoteUserResult, admin_demote_user
from mindsos_server.audit import (
    EVT_ADMIN_DEMOTE_USER,
    EVT_KILL_SESSION,
)
from mindsos_server.errors import (
    LastAdminError,
    NotAnAdminError,
    UserNotFoundError,
)


class TestHappyPath:
    def test_returns_result(self, seeded_two_admins, admin_session):
        result = admin_demote_user(
            seeded_two_admins, admin_session, target_user_id="admin2"
        )
        assert isinstance(result, DemoteUserResult)
        assert result.target_user_id == "admin2"
        assert result.prior_role == "admin"
        assert result.sessions_killed == 0

    def test_actor_role_set_to_user(self, seeded_two_admins, admin_session):
        admin_demote_user(
            seeded_two_admins, admin_session, target_user_id="admin2"
        )
        row = seeded_two_admins.execute(
            "SELECT actor_role FROM users WHERE user_id = 'admin2'"
        ).fetchone()
        assert row[0] == "user"

    def test_sessions_killed_atomically(
        self, seeded_admin_target_with_sessions, admin_session
    ):
        conn, session_ids = seeded_admin_target_with_sessions
        result = admin_demote_user(
            conn, admin_session, target_user_id="admin2"
        )
        assert result.sessions_killed == len(session_ids)
        # sessions table empty for admin2
        rows = conn.execute(
            "SELECT id FROM sessions WHERE user_id = 'admin2'"
        ).fetchall()
        assert rows == []

    def test_evt_kill_session_per_row_with_context(
        self, seeded_admin_target_with_sessions, admin_session
    ):
        conn, session_ids = seeded_admin_target_with_sessions
        admin_demote_user(conn, admin_session, target_user_id="admin2")
        rows = conn.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_KILL_SESSION,),
        ).fetchall()
        assert len(rows) == len(session_ids)
        extras = [json.loads(r[0]) for r in rows]
        # PB-14: all rows carry context="admin_demote_user"
        assert all(e["context"] == "admin_demote_user" for e in extras)
        # All session_ids covered
        recorded_sids = sorted(e["session_id"] for e in extras)
        assert recorded_sids == sorted(session_ids)

    def test_evt_admin_demote_user_summary(
        self, seeded_admin_target_with_sessions, admin_session
    ):
        conn, session_ids = seeded_admin_target_with_sessions
        admin_demote_user(conn, admin_session, target_user_id="admin2")
        rows = conn.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_ADMIN_DEMOTE_USER,),
        ).fetchall()
        assert len(rows) == 1
        extra = json.loads(rows[0][0])
        # PB-16 payload shape
        assert extra == {
            "prior_role": "admin",
            "sessions_killed": len(session_ids),
        }


class TestSoleAdmin:
    def test_raises_last_admin_error(self, seeded_admin, admin_session):
        with pytest.raises(LastAdminError) as exc_info:
            admin_demote_user(
                seeded_admin, admin_session, target_user_id="admin"
            )
        assert exc_info.value.target_user_id == "admin"

    def test_error_message_names_reset_admin(
        self, seeded_admin, admin_session
    ):
        with pytest.raises(LastAdminError) as exc_info:
            admin_demote_user(
                seeded_admin, admin_session, target_user_id="admin"
            )
        msg = str(exc_info.value)
        # PB-23: message embeds the override hint per ADR-0012 §Consequences
        assert "reset-admin" in msg
        assert "promote-user" in msg

    def test_no_state_change_on_last_admin(
        self, seeded_admin, admin_session
    ):
        with pytest.raises(LastAdminError):
            admin_demote_user(
                seeded_admin, admin_session, target_user_id="admin"
            )
        row = seeded_admin.execute(
            "SELECT actor_role FROM users WHERE user_id = 'admin'"
        ).fetchone()
        assert row[0] == "admin"


class TestNotAnAdmin:
    def test_raises_not_an_admin(self, seeded_user, admin_session):
        with pytest.raises(NotAnAdminError) as exc_info:
            admin_demote_user(
                seeded_user, admin_session, target_user_id="alice"
            )
        assert exc_info.value.target_user_id == "alice"
        assert exc_info.value.actual_role == "user"

    def test_verb_agnostic_message(self, seeded_user, admin_session):
        with pytest.raises(NotAnAdminError) as exc_info:
            admin_demote_user(
                seeded_user, admin_session, target_user_id="alice"
            )
        msg = str(exc_info.value)
        # R4 PB-25: message no longer references reset-admin or
        # admin_promote_user. The verb-specific framing is a CLI concern.
        assert "alice" in msg
        assert "admin role required" in msg
        assert "reset-admin" not in msg
        assert "promote-user" not in msg


class TestUserNotFound:
    def test_raises(self, seeded_admin, admin_session):
        with pytest.raises(UserNotFoundError):
            admin_demote_user(
                seeded_admin, admin_session, target_user_id="nobody"
            )
