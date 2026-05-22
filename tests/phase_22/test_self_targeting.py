"""
Phase 22 R2 PB-18 — admin self-targeting allowed (no SelfTargetError).

ADR-0012 §Rationale: "filesystem access is the acceptable authority
floor" — operator can target themselves via the admin verbs as long
as the sole-admin invariant holds. Theatrical self-protection adds
complexity for marginal benefit; reset-admin via filesystem is the
recovery floor.

Tests verify:
* Self-demote allowed if another admin exists.
* Self-demote raises LastAdminError if sole admin (helper-gated).
* Self-disable allowed with a peer admin.
* Self-kill-session allowed.
"""

from __future__ import annotations

import pytest

from mindsos_server.admin import (
    admin_demote_user,
    admin_disable_user,
    admin_kill_session,
)
from mindsos_server.errors import LastAdminError
from mindsos_server.session import Session


class TestSelfTargeting:
    def test_self_demote_allowed_with_peer_admin(
        self, seeded_two_admins, insert_extra_session
    ):
        # 'admin2' is the caller AND the target.
        caller = Session.for_testing("admin2", is_admin=True)
        result = admin_demote_user(
            seeded_two_admins, caller, target_user_id="admin2"
        )
        assert result.target_user_id == "admin2"
        row = seeded_two_admins.execute(
            "SELECT actor_role FROM users WHERE user_id = 'admin2'"
        ).fetchone()
        assert row[0] == "user"

    def test_self_demote_raises_when_sole_admin(self, seeded_admin):
        caller = Session.for_testing("admin", is_admin=True)
        with pytest.raises(LastAdminError):
            admin_demote_user(
                seeded_admin, caller, target_user_id="admin"
            )

    def test_self_disable_allowed_with_peer_admin(self, seeded_two_admins):
        caller = Session.for_testing("admin2", is_admin=True)
        result = admin_disable_user(
            seeded_two_admins, caller, target_user_id="admin2"
        )
        assert result.target_user_id == "admin2"

    def test_self_kill_session_allowed(
        self, seeded_user_with_sessions, insert_extra_session
    ):
        conn, _ = seeded_user_with_sessions
        # admin caller has their own session row
        caller_sid = insert_extra_session(conn, "admin", "0")
        caller = Session.for_testing("admin", is_admin=True)
        result = admin_kill_session(
            conn, caller, target_session_id=caller_sid
        )
        assert result.target_session_id == caller_sid
        assert result.target_user_id == "admin"
        # Session row is gone
        rows = conn.execute(
            "SELECT session_id FROM sessions WHERE session_id = ?",
            (caller_sid,),
        ).fetchall()
        assert rows == []
