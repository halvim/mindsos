"""
Phase 22 R1 PB-10 + R2 PB-15 — admin_enable_user.

Covers:
* Happy path: disabled=0; audit emitted.
* Idempotent on already-enabled (audit-always per R1 PB-10).
* UserNotFoundError on missing.
* No session-kill side effect (enable is the safer direction).
"""

from __future__ import annotations

import json

import pytest

from mindsos_server.admin import EnableUserResult, admin_enable_user
from mindsos_server.audit import (
    EVT_ADMIN_ENABLE_USER,
    EVT_KILL_SESSION,
)
from mindsos_server.errors import UserNotFoundError


class TestHappyPath:
    def test_returns_result(self, seeded_disabled_user, admin_session):
        result = admin_enable_user(
            seeded_disabled_user, admin_session, target_user_id="alice"
        )
        assert isinstance(result, EnableUserResult)
        assert result.target_user_id == "alice"
        assert result.was_already_enabled is False

    def test_disabled_cleared(self, seeded_disabled_user, admin_session):
        admin_enable_user(
            seeded_disabled_user, admin_session, target_user_id="alice"
        )
        row = seeded_disabled_user.execute(
            "SELECT disabled FROM users WHERE user_id = 'alice'"
        ).fetchone()
        assert int(row[0]) == 0

    def test_evt_admin_enable_user_emitted(
        self, seeded_disabled_user, admin_session
    ):
        admin_enable_user(
            seeded_disabled_user, admin_session, target_user_id="alice"
        )
        rows = seeded_disabled_user.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_ADMIN_ENABLE_USER,),
        ).fetchall()
        assert len(rows) == 1
        extra = json.loads(rows[0][0])
        assert extra == {"was_already_enabled": False}


class TestIdempotency:
    def test_already_enabled_marker(self, seeded_user, admin_session):
        # 'alice' is enabled (disabled=0) by default
        result = admin_enable_user(
            seeded_user, admin_session, target_user_id="alice"
        )
        assert result.was_already_enabled is True

    def test_already_enabled_audit_always_emitted(
        self, seeded_user, admin_session
    ):
        admin_enable_user(seeded_user, admin_session, target_user_id="alice")
        rows = seeded_user.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_ADMIN_ENABLE_USER,),
        ).fetchall()
        # PB-10: audit always, even on no-op
        assert len(rows) == 1
        extra = json.loads(rows[0][0])
        assert extra["was_already_enabled"] is True


class TestNoSessionKill:
    def test_no_evt_kill_session(
        self, seeded_disabled_user, admin_session, insert_extra_session
    ):
        # Add a session for alice (synthetic; doesn't pre-validate disabled)
        insert_extra_session(seeded_disabled_user, "alice", "0")
        admin_enable_user(
            seeded_disabled_user, admin_session, target_user_id="alice"
        )
        rows = seeded_disabled_user.execute(
            "SELECT id FROM audit WHERE event = ?",
            (EVT_KILL_SESSION,),
        ).fetchall()
        # Enable does NOT kill sessions
        assert rows == []


class TestUserNotFound:
    def test_raises(self, seeded_admin, admin_session):
        with pytest.raises(UserNotFoundError):
            admin_enable_user(
                seeded_admin, admin_session, target_user_id="nobody"
            )
