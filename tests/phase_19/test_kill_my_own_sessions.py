"""
Phase 19 kill_my_own_sessions() tests per ADR-0005 + PB-9.

Verifies:
* Returns count of sessions killed (0 if none, N if N existed).
* Calls verify() for fresh credentials gating — wrong password raises
  AuthFailedError + writes EVT_LOGIN_FAILED with `context=kill_my_own_sessions`.
* All sessions for user_id deleted in one transaction.
* Other users' sessions are untouched.
* Per-row EVT_LOGOUT audit emitted (PB-9 — caller-owned audit).
"""

from __future__ import annotations

import pytest

from mindsos_server.audit import EVT_LOGIN_FAILED, EVT_LOGOUT
from mindsos_server.errors import AuthFailedError
from mindsos_server.sessions import kill_my_own_sessions, login


def _bypass_concurrent_check_and_insert_extra_session(
    conn, user_id: str, *, n: int = 1
) -> None:
    """Insert extra sessions directly via SQL to test multi-kill (login
    refuses concurrent, so we can't ship 2 via the public API)."""
    ts = "2026-05-21T00:00:00.000Z"
    for i in range(n):
        conn.execute(
            "INSERT INTO sessions "
            "(session_id, user_id, token_hash, created_at, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"extra-{user_id}-{i}", user_id, f"hash-{user_id}-{i}", ts, ts),
        )
    conn.commit()


class TestHappyPath:
    def test_kill_zero_sessions_returns_zero(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        count = kill_my_own_sessions(
            seeded_admin,
            "admin",
            "adminpw",
            ttl=fast_ttl,
            params=fast_params,
        )
        assert count == 0

    def test_kill_single_session(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        login(seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params)
        count = kill_my_own_sessions(
            seeded_admin,
            "admin",
            "adminpw",
            ttl=fast_ttl,
            params=fast_params,
        )
        assert count == 1
        rows = seeded_admin.execute(
            "SELECT session_id FROM sessions WHERE user_id = 'admin'"
        ).fetchall()
        assert rows == []

    def test_kill_multiple_sessions(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        # Direct-insert two extra sessions (bypassing concurrent-login
        # check which only login() enforces).
        _bypass_concurrent_check_and_insert_extra_session(
            seeded_admin, "admin", n=3
        )
        count = kill_my_own_sessions(
            seeded_admin,
            "admin",
            "adminpw",
            ttl=fast_ttl,
            params=fast_params,
        )
        assert count == 3

    def test_per_session_audit_emitted(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        _bypass_concurrent_check_and_insert_extra_session(
            seeded_admin, "admin", n=2
        )
        kill_my_own_sessions(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        rows = seeded_admin.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_LOGOUT,),
        ).fetchall()
        # 2 EVT_LOGOUT rows; each carries context=kill_my_own_sessions.
        assert len(rows) == 2
        for (extra_json,) in rows:
            assert "kill_my_own_sessions" in extra_json


class TestFreshCredentialsGate:
    """ADR-0005 + PB-9 — verify() runs; wrong creds reject + audit."""

    def test_wrong_password_raises(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        with pytest.raises(AuthFailedError):
            kill_my_own_sessions(
                seeded_admin,
                "admin",
                "wrong",
                ttl=fast_ttl,
                params=fast_params,
            )

    def test_wrong_password_audits_with_context(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        with pytest.raises(AuthFailedError):
            kill_my_own_sessions(
                seeded_admin,
                "admin",
                "wrong",
                ttl=fast_ttl,
                params=fast_params,
            )
        rows = seeded_admin.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_LOGIN_FAILED,),
        ).fetchall()
        assert len(rows) == 1
        # PB-9 — caller-owned audit with context distinguishing this from
        # a real login failure.
        assert "kill_my_own_sessions" in rows[0][0]
        assert "BAD_PASSWORD" in rows[0][0]


class TestOtherUsersUntouched:
    def test_only_target_user_sessions_killed(
        self, seeded_admin, seeded_user, fast_params, fast_ttl
    ) -> None:
        # NOTE: seeded_admin + seeded_user fixtures both yield the same
        # tmp_server_db; their composition results in both users in the
        # same DB.
        # Insert sessions for both users.
        _bypass_concurrent_check_and_insert_extra_session(
            seeded_admin, "admin", n=2
        )
        _bypass_concurrent_check_and_insert_extra_session(
            seeded_admin, "alice", n=1
        )

        kill_my_own_sessions(
            seeded_admin,
            "admin",
            "adminpw",
            ttl=fast_ttl,
            params=fast_params,
        )

        # admin sessions all gone; alice's untouched.
        admin_rows = seeded_admin.execute(
            "SELECT session_id FROM sessions WHERE user_id = 'admin'"
        ).fetchall()
        alice_rows = seeded_admin.execute(
            "SELECT session_id FROM sessions WHERE user_id = 'alice'"
        ).fetchall()
        assert admin_rows == []
        assert len(alice_rows) == 1
