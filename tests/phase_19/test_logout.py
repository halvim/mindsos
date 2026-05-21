"""
Phase 19 logout() tests per PB-11 + minor lock.

Verifies:
* logout(valid token) → True; row deleted; EVT_LOGOUT audit row.
* logout(invalid token) → False; no audit row; no exception.
* logout(empty string) → False; silent no-op.
* logout twice → second call no-op.
"""

from __future__ import annotations

import pytest

from mindsos_server.audit import EVT_LOGOUT
from mindsos_server.sessions import login, logout


class TestLogoutHappyPath:
    def test_returns_true_on_delete(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        assert logout(seeded_admin, result.token) is True

    def test_session_row_deleted(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        logout(seeded_admin, result.token)
        rows = seeded_admin.execute(
            "SELECT session_id FROM sessions WHERE session_id = ?",
            (result.session.session_id,),
        ).fetchall()
        assert rows == []

    def test_evt_logout_audited(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        logout(seeded_admin, result.token)
        rows = seeded_admin.execute(
            "SELECT event, actor_user FROM audit WHERE event = ?",
            (EVT_LOGOUT,),
        ).fetchall()
        assert len(rows) == 1
        assert rows[0] == (EVT_LOGOUT, "admin")


class TestLogoutSilentNoOp:
    """Minor lock: invalid/expired/missing token is a silent no-op."""

    def test_invalid_token_returns_false(self, tmp_server_db) -> None:
        assert logout(tmp_server_db, "this-token-was-never-issued") is False

    def test_empty_token_returns_false(self, tmp_server_db) -> None:
        assert logout(tmp_server_db, "") is False

    def test_invalid_token_writes_no_audit(self, tmp_server_db) -> None:
        logout(tmp_server_db, "garbage")
        rows = tmp_server_db.execute(
            "SELECT * FROM audit WHERE event = ?", (EVT_LOGOUT,)
        ).fetchall()
        assert rows == []

    def test_double_logout_idempotent(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        assert logout(seeded_admin, result.token) is True
        # Second call: row already gone; should be silent no-op.
        assert logout(seeded_admin, result.token) is False
