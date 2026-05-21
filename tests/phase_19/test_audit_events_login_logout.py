"""
Phase 19 audit-event firing tests per ADR-0013 + PB-9 + PB-3.

Verifies that the four Phase 19 audit events fire at the expected
sites with the expected ``extra_json`` payload shapes:
* EVT_LOGIN — on successful login; extra_json includes session_id.
* EVT_LOGIN_FAILED — caller-owned (PB-9); written by login + by
  kill_my_own_sessions; carries `cause` in extra_json.
* EVT_LOGIN_REJECTED_CONCURRENT — written by login on
  AlreadyLoggedInError; carries existing_session_id + existing_created_at.
* EVT_LOGOUT — written by logout() + kill_my_own_sessions().
"""

from __future__ import annotations

import json

import pytest

from mindsos_server.audit import (
    EVT_LOGIN,
    EVT_LOGIN_FAILED,
    EVT_LOGIN_REJECTED_CONCURRENT,
    EVT_LOGOUT,
)
from mindsos_server.errors import AlreadyLoggedInError, AuthFailedError
from mindsos_server.sessions import login, logout


class TestEvtLogin:
    def test_extra_json_contains_session_id(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        row = seeded_admin.execute(
            "SELECT extra_json FROM audit WHERE event = ?", (EVT_LOGIN,)
        ).fetchone()
        decoded = json.loads(row[0])
        assert decoded["session_id"] == result.session.session_id


class TestEvtLoginFailed:
    def test_extra_json_carries_cause(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        with pytest.raises(AuthFailedError):
            login(
                seeded_admin, "admin", "wrong", ttl=fast_ttl, params=fast_params
            )
        row = seeded_admin.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_LOGIN_FAILED,),
        ).fetchone()
        decoded = json.loads(row[0])
        assert decoded["cause"] == "BAD_PASSWORD"


class TestEvtLoginRejectedConcurrent:
    def test_extra_json_carries_existing(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        first = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        with pytest.raises(AlreadyLoggedInError):
            login(
                seeded_admin,
                "admin",
                "adminpw",
                ttl=fast_ttl,
                params=fast_params,
            )
        row = seeded_admin.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_LOGIN_REJECTED_CONCURRENT,),
        ).fetchone()
        decoded = json.loads(row[0])
        assert decoded["existing_session_id"] == first.session.session_id
        assert "existing_created_at" in decoded
        # PB-3: payload has NO `source` field.
        assert "source" not in decoded


class TestEvtLogout:
    def test_logout_writes_evt_logout(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        logout(seeded_admin, result.token)
        rows = seeded_admin.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_LOGOUT,),
        ).fetchall()
        assert len(rows) == 1
        decoded = json.loads(rows[0][0])
        assert decoded["session_id"] == result.session.session_id


class TestAuditAllInSameTransaction:
    """ADR-0013 §Decision — state change + audit in one transaction."""

    def test_login_state_and_audit_committed_together(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        login(seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params)
        # Both visible after one commit (login() commits at the end).
        sess_count = seeded_admin.execute(
            "SELECT COUNT(*) FROM sessions WHERE user_id = 'admin'"
        ).fetchone()[0]
        audit_count = seeded_admin.execute(
            "SELECT COUNT(*) FROM audit WHERE event = ?", (EVT_LOGIN,)
        ).fetchone()[0]
        assert sess_count == 1
        assert audit_count == 1
