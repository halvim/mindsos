"""
Phase 22 R1 PB-3 + R1 PB-5 + R2 PB-12 — admin_promote_user.

Covers:
* Happy path: user → admin; UPDATE applied; EVT_ADMIN_PROMOTE_USER emitted.
* AlreadyAnAdminError on admin target (PB-3: no idempotent re-promote).
* UserNotFoundError on missing target.
* Disabled target: disabled flag left unchanged (PB-12 — no auto-enable).
* Silent: no EVT_KILL_SESSION for promotee with active sessions (PB-5).
"""

from __future__ import annotations

import pytest

from mindsos_server.admin import PromoteUserResult, admin_promote_user
from mindsos_server.audit import (
    EVT_ADMIN_PROMOTE_USER,
    EVT_KILL_SESSION,
)
from mindsos_server.errors import (
    AlreadyAnAdminError,
    UserNotFoundError,
)


class TestHappyPath:
    def test_returns_result(self, seeded_user, admin_session):
        result = admin_promote_user(
            seeded_user, admin_session, target_user_id="alice"
        )
        assert isinstance(result, PromoteUserResult)
        assert result.target_user_id == "alice"
        assert result.prior_role == "user"
        assert result.ts.endswith("Z")

    def test_users_row_updated(self, seeded_user, admin_session):
        admin_promote_user(seeded_user, admin_session, target_user_id="alice")
        row = seeded_user.execute(
            "SELECT actor_role FROM users WHERE user_id = 'alice'"
        ).fetchone()
        assert row[0] == "admin"

    def test_evt_admin_promote_user_emitted(self, seeded_user, admin_session):
        admin_promote_user(seeded_user, admin_session, target_user_id="alice")
        rows = seeded_user.execute(
            "SELECT actor_user, target_user, extra_json FROM audit "
            "WHERE event = ?",
            (EVT_ADMIN_PROMOTE_USER,),
        ).fetchall()
        assert len(rows) == 1
        actor, target, extra = rows[0]
        assert actor == "admin-caller"
        assert target == "alice"
        import json
        assert json.loads(extra) == {"prior_role": "user"}


class TestAlreadyAnAdmin:
    def test_raises_on_admin_target(self, seeded_two_admins, admin_session):
        with pytest.raises(AlreadyAnAdminError) as exc_info:
            admin_promote_user(
                seeded_two_admins, admin_session, target_user_id="admin2"
            )
        assert exc_info.value.target_user_id == "admin2"

    def test_no_audit_row_on_error(self, seeded_two_admins, admin_session):
        with pytest.raises(AlreadyAnAdminError):
            admin_promote_user(
                seeded_two_admins, admin_session, target_user_id="admin2"
            )
        rows = seeded_two_admins.execute(
            "SELECT id FROM audit WHERE event = ?",
            (EVT_ADMIN_PROMOTE_USER,),
        ).fetchall()
        assert rows == []

    def test_users_row_unchanged(self, seeded_two_admins, admin_session):
        with pytest.raises(AlreadyAnAdminError):
            admin_promote_user(
                seeded_two_admins, admin_session, target_user_id="admin2"
            )
        row = seeded_two_admins.execute(
            "SELECT actor_role FROM users WHERE user_id = 'admin2'"
        ).fetchone()
        assert row[0] == "admin"


class TestUserNotFound:
    def test_raises_user_not_found(self, seeded_admin, admin_session):
        with pytest.raises(UserNotFoundError) as exc_info:
            admin_promote_user(
                seeded_admin, admin_session, target_user_id="nobody"
            )
        assert exc_info.value.target_user_id == "nobody"


class TestDisabledTarget:
    def test_disabled_flag_unchanged_after_promote(
        self, seeded_disabled_user, admin_session
    ):
        admin_promote_user(
            seeded_disabled_user, admin_session, target_user_id="alice"
        )
        row = seeded_disabled_user.execute(
            "SELECT actor_role, disabled FROM users WHERE user_id = 'alice'"
        ).fetchone()
        assert row[0] == "admin"
        # PB-12: disabled flag NOT auto-cleared
        assert int(row[1]) == 1


class TestSilentPromote:
    def test_no_evt_kill_session_emitted(
        self, seeded_user_with_sessions, admin_session, insert_extra_session
    ):
        conn, _ = seeded_user_with_sessions
        admin_promote_user(conn, admin_session, target_user_id="alice")
        rows = conn.execute(
            "SELECT id FROM audit WHERE event = ?",
            (EVT_KILL_SESSION,),
        ).fetchall()
        # PB-5: promote is silent — no session kill on cap expansion
        assert rows == []

    def test_sessions_table_unchanged(
        self, seeded_user_with_sessions, admin_session
    ):
        conn, session_ids = seeded_user_with_sessions
        admin_promote_user(conn, admin_session, target_user_id="alice")
        rows = conn.execute(
            "SELECT session_id FROM sessions WHERE user_id = 'alice'"
        ).fetchall()
        kept = sorted(r[0] for r in rows)
        assert kept == sorted(session_ids)
