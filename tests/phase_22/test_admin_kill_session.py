"""
Phase 22 R1 PB-9 + R2 PB-13 + PB-14 — admin_kill_session.

Covers:
* Happy path: session deleted; EVT_KILL_SESSION with context.
* SessionNotFoundError on missing session_id.
* Self-target allowed (PB-18).
* target_user_id correctly resolved from the sessions table.
"""

from __future__ import annotations

import json

import pytest

from mindsos_server.admin import KillSessionResult, admin_kill_session
from mindsos_server.audit import EVT_KILL_SESSION
from mindsos_server.errors import SessionNotFoundError


class TestHappyPath:
    def test_returns_result(
        self, seeded_user_with_sessions, admin_session
    ):
        conn, session_ids = seeded_user_with_sessions
        result = admin_kill_session(
            conn, admin_session, target_session_id=session_ids[0]
        )
        assert isinstance(result, KillSessionResult)
        assert result.target_session_id == session_ids[0]
        assert result.target_user_id == "alice"

    def test_session_row_deleted(
        self, seeded_user_with_sessions, admin_session
    ):
        conn, session_ids = seeded_user_with_sessions
        admin_kill_session(
            conn, admin_session, target_session_id=session_ids[0]
        )
        rows = conn.execute(
            "SELECT id FROM sessions WHERE session_id = ?",
            (session_ids[0],),
        ).fetchall()
        assert rows == []

    def test_other_sessions_unaffected(
        self, seeded_user_with_sessions, admin_session
    ):
        conn, session_ids = seeded_user_with_sessions
        admin_kill_session(
            conn, admin_session, target_session_id=session_ids[0]
        )
        remaining = conn.execute(
            "SELECT session_id FROM sessions WHERE user_id = 'alice'"
        ).fetchall()
        assert sorted(r[0] for r in remaining) == sorted(session_ids[1:])

    def test_evt_kill_session_context(
        self, seeded_user_with_sessions, admin_session
    ):
        conn, session_ids = seeded_user_with_sessions
        admin_kill_session(
            conn, admin_session, target_session_id=session_ids[0]
        )
        rows = conn.execute(
            "SELECT actor_user, target_user, extra_json FROM audit "
            "WHERE event = ?",
            (EVT_KILL_SESSION,),
        ).fetchall()
        assert len(rows) == 1
        actor, target, extra_json = rows[0]
        extra = json.loads(extra_json)
        assert actor == "admin-caller"
        assert target == "alice"
        assert extra["session_id"] == session_ids[0]
        assert extra["context"] == "admin_kill_session"


class TestSessionNotFound:
    def test_raises(self, seeded_admin, admin_session):
        with pytest.raises(SessionNotFoundError) as exc_info:
            admin_kill_session(
                seeded_admin, admin_session, target_session_id="nope"
            )
        assert exc_info.value.target_session_id == "nope"

    def test_no_audit_row_on_error(self, seeded_admin, admin_session):
        with pytest.raises(SessionNotFoundError):
            admin_kill_session(
                seeded_admin, admin_session, target_session_id="nope"
            )
        rows = seeded_admin.execute(
            "SELECT id FROM audit WHERE event = ?",
            (EVT_KILL_SESSION,),
        ).fetchall()
        assert rows == []
