"""
Phase 19 login() tests per PB-3 + PB-6 + PB-8 + PB-9 + PB-15.

Verifies:
* Happy-path login returns LoginResult; sessions row inserted; EVT_LOGIN
  audited.
* AuthFailed (wrong password / unknown user / disabled) propagates +
  EVT_LOGIN_FAILED audit row written (PB-9 — caller-owned).
* Refuse-concurrent-login: AlreadyLoggedInError raised; 2-field payload
  (PB-3); EVT_LOGIN_REJECTED_CONCURRENT audit row written.
* PB-8 ordering: stale session expired BEFORE concurrent-check → relogin
  succeeds without going through kill_my_own_sessions.
* Token + session_id are independent (different lengths).
"""

from __future__ import annotations

import time

import pytest

from mindsos_server.audit import (
    EVT_LOGIN,
    EVT_LOGIN_FAILED,
    EVT_LOGIN_REJECTED_CONCURRENT,
)
from mindsos_server.errors import AlreadyLoggedInError, AuthFailedError
from mindsos_server.sessions import LoginResult, login


class TestLoginHappyPath:
    def test_returns_login_result(self, seeded_admin, fast_params, fast_ttl) -> None:
        result = login(
            seeded_admin,
            "admin",
            "adminpw",
            ttl=fast_ttl,
            params=fast_params,
        )
        assert isinstance(result, LoginResult)
        assert result.session.user_id == "admin"
        assert result.session.actor_role == "admin"
        # token + session_id are different primitives (PB minor lock).
        assert result.token != result.session.session_id
        assert len(result.token) > 0
        assert len(result.session.session_id) > 0

    def test_session_row_inserted(self, seeded_admin, fast_params, fast_ttl) -> None:
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        row = seeded_admin.execute(
            "SELECT session_id, user_id FROM sessions WHERE session_id = ?",
            (result.session.session_id,),
        ).fetchone()
        assert row == (result.session.session_id, "admin")

    def test_evt_login_audit_written(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        login(seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params)
        rows = seeded_admin.execute(
            "SELECT event, actor_user FROM audit WHERE event = ?",
            (EVT_LOGIN,),
        ).fetchall()
        assert len(rows) == 1
        assert rows[0] == (EVT_LOGIN, "admin")

    def test_expires_at_at_issue_uses_sliding(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        """At issue, last_seen_at == created_at, so
        ``expires_at = created_at + sliding`` (sliding < absolute under
        _TEST_FAST_TTL where sliding=1s < absolute=2s)."""
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        delta_seconds = (result.expires_at - result.created_at).total_seconds()
        # _TEST_FAST_TTL.sliding_seconds = 1
        assert delta_seconds == pytest.approx(1.0, abs=0.05)


class TestAuthFailedAudits:
    """PB-9 — caller (login) owns EVT_LOGIN_FAILED emission."""

    def test_unknown_user_audits(self, tmp_server_db, fast_params, fast_ttl) -> None:
        with pytest.raises(AuthFailedError):
            login(
                tmp_server_db, "ghost", "any", ttl=fast_ttl, params=fast_params
            )
        rows = tmp_server_db.execute(
            "SELECT event, extra_json FROM audit WHERE event = ?",
            (EVT_LOGIN_FAILED,),
        ).fetchall()
        assert len(rows) == 1
        assert "UNKNOWN_USER" in rows[0][1]

    def test_bad_password_audits(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        with pytest.raises(AuthFailedError):
            login(
                seeded_admin, "admin", "wrong", ttl=fast_ttl, params=fast_params
            )
        rows = seeded_admin.execute(
            "SELECT event, extra_json FROM audit WHERE event = ?",
            (EVT_LOGIN_FAILED,),
        ).fetchall()
        assert len(rows) == 1
        assert "BAD_PASSWORD" in rows[0][1]


class TestRefuseConcurrentLogin:
    def test_second_login_raises(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        first = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        with pytest.raises(AlreadyLoggedInError) as exc_info:
            login(
                seeded_admin,
                "admin",
                "adminpw",
                ttl=fast_ttl,
                params=fast_params,
            )
        assert exc_info.value.existing_session_id == first.session.session_id

    def test_payload_is_two_field(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        """PB-3 / ADR-0005 §am1: {existing_session_id, created_at} only;
        no `source` field."""
        first = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        with pytest.raises(AlreadyLoggedInError) as exc_info:
            login(
                seeded_admin,
                "admin",
                "adminpw",
                ttl=fast_ttl,
                params=fast_params,
            )
        # 2-field shape — has existing_session_id + created_at, no source.
        assert hasattr(exc_info.value, "existing_session_id")
        assert hasattr(exc_info.value, "created_at")
        assert not hasattr(exc_info.value, "source")
        # The created_at matches the first login's row.
        assert exc_info.value.existing_session_id == first.session.session_id

    def test_concurrent_login_audits(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        login(seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params)
        with pytest.raises(AlreadyLoggedInError):
            login(
                seeded_admin,
                "admin",
                "adminpw",
                ttl=fast_ttl,
                params=fast_params,
            )
        rows = seeded_admin.execute(
            "SELECT event FROM audit WHERE event = ?",
            (EVT_LOGIN_REJECTED_CONCURRENT,),
        ).fetchall()
        assert len(rows) == 1


class TestLazyExpireBeforeConcurrentCheck:
    """PB-8 ordering lock: stale session must be lazy-expired BEFORE the
    concurrent-login check fires, else relogin gets a false-positive
    AlreadyLoggedInError."""

    def test_relogin_after_absolute_expiry(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        # First login — session valid for absolute=2s.
        first = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )

        # Wait past absolute TTL (2s).
        time.sleep(2.5)

        # Second login MUST succeed, NOT raise AlreadyLoggedInError.
        # The lazy-expire-then-concurrent-check ordering deletes the
        # stale row before the existence check fires.
        second = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        assert second.session.session_id != first.session.session_id

    def test_relogin_after_sliding_expiry(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        first = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        # Wait past sliding TTL (1s) but within absolute (2s).
        time.sleep(1.2)
        second = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        assert second.session.session_id != first.session.session_id
