"""
Phase 22 R1 PB-6 + R2 PB-14 + PB-15 — admin_disable_user.

Covers:
* Happy path: disabled=1; sessions killed; audits emitted.
* Idempotent on already-disabled (R2 PB-15 audit-always with
  ``was_already_disabled`` marker).
* Sole-admin invariant fires on active sole-admin target.
* Sole-admin invariant SKIPPED for already-disabled admin (target was
  already excluded from active-admin set).
* UserNotFoundError on missing target.
* Per-row EVT_KILL_SESSION with context="admin_disable_user".
"""

from __future__ import annotations

import json

import pytest

from mindsos_server.admin import DisableUserResult, admin_disable_user
from mindsos_server.audit import (
    EVT_ADMIN_DISABLE_USER,
    EVT_KILL_SESSION,
)
from mindsos_server.errors import LastAdminError, UserNotFoundError


class TestHappyPath:
    def test_returns_result(self, seeded_user, admin_session):
        result = admin_disable_user(
            seeded_user, admin_session, target_user_id="alice"
        )
        assert isinstance(result, DisableUserResult)
        assert result.target_user_id == "alice"
        assert result.was_already_disabled is False

    def test_disabled_flag_set(self, seeded_user, admin_session):
        admin_disable_user(seeded_user, admin_session, target_user_id="alice")
        row = seeded_user.execute(
            "SELECT disabled FROM users WHERE user_id = 'alice'"
        ).fetchone()
        assert int(row[0]) == 1

    def test_sessions_killed(
        self, seeded_user_with_sessions, admin_session
    ):
        conn, session_ids = seeded_user_with_sessions
        result = admin_disable_user(
            conn, admin_session, target_user_id="alice"
        )
        assert result.sessions_killed == len(session_ids)
        rows = conn.execute(
            "SELECT id FROM sessions WHERE user_id = 'alice'"
        ).fetchall()
        assert rows == []

    def test_evt_kill_session_context(
        self, seeded_user_with_sessions, admin_session
    ):
        conn, _ = seeded_user_with_sessions
        admin_disable_user(conn, admin_session, target_user_id="alice")
        rows = conn.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_KILL_SESSION,),
        ).fetchall()
        for r in rows:
            extra = json.loads(r[0])
            assert extra["context"] == "admin_disable_user"

    def test_evt_admin_disable_user_summary(
        self, seeded_user_with_sessions, admin_session
    ):
        conn, session_ids = seeded_user_with_sessions
        admin_disable_user(conn, admin_session, target_user_id="alice")
        rows = conn.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_ADMIN_DISABLE_USER,),
        ).fetchall()
        assert len(rows) == 1
        extra = json.loads(rows[0][0])
        assert extra == {
            "was_already_disabled": False,
            "sessions_killed": len(session_ids),
        }


class TestIdempotency:
    def test_already_disabled_marker(
        self, seeded_disabled_user, admin_session
    ):
        result = admin_disable_user(
            seeded_disabled_user, admin_session, target_user_id="alice"
        )
        # PB-15: idempotent + audit always; marker records the no-op state
        assert result.was_already_disabled is True

    def test_already_disabled_audit_emitted(
        self, seeded_disabled_user, admin_session
    ):
        admin_disable_user(
            seeded_disabled_user, admin_session, target_user_id="alice"
        )
        rows = seeded_disabled_user.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_ADMIN_DISABLE_USER,),
        ).fetchall()
        assert len(rows) == 1
        extra = json.loads(rows[0][0])
        assert extra["was_already_disabled"] is True


class TestSoleAdmin:
    def test_disabling_sole_active_admin_raises(
        self, seeded_admin, admin_session
    ):
        with pytest.raises(LastAdminError):
            admin_disable_user(
                seeded_admin, admin_session, target_user_id="admin"
            )

    def test_disabling_already_disabled_admin_does_not_raise(
        self, seeded_disabled_admin_extra, admin_session
    ):
        # 'admin2' is disabled=1 already; 'admin' is the sole ACTIVE admin.
        # Disabling 'admin2' is idempotent and does NOT trigger LastAdminError
        # because count of active admins is unchanged.
        result = admin_disable_user(
            seeded_disabled_admin_extra,
            admin_session,
            target_user_id="admin2",
        )
        assert result.was_already_disabled is True


class TestUserNotFound:
    def test_raises(self, seeded_admin, admin_session):
        with pytest.raises(UserNotFoundError):
            admin_disable_user(
                seeded_admin, admin_session, target_user_id="nobody"
            )
