"""
PB-9 / ADR-0013 §amendment-1 regression guard.

Phase 18 originally baked ``EVT_LOGIN_FAILED`` audit-write inside
:func:`mindsos_server.users.verify`. Phase 19 PB-9 refactored verify()
to be a pure predicate so :func:`mindsos_server.sessions.kill_my_own_sessions`
doesn't produce a semantically-wrong audit event (login-failed event
for what is actually a recovery attempt).

These tests assert verify() writes ZERO audit rows on every failure
path (UNKNOWN_USER / BAD_PASSWORD / DISABLED) and on the success path.
Counterpart positive assertions (that login() and kill_my_own_sessions()
DO write audit) live in :mod:`tests.phase_19.test_audit_events_login_logout`.
"""

from __future__ import annotations

import pytest

from mindsos_server._argon2 import Argon2Params
from mindsos_server.errors import AuthFailedError, AuthFailureCause
from mindsos_server.users import _insert_first_admin, verify


def _audit_row_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]


def _audit_login_failed_count(conn) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM audit WHERE event = ?",
        ("EVT_LOGIN_FAILED",),
    ).fetchone()[0]


class TestVerifyNeverAuditsLoginFailed:
    def test_unknown_user_writes_no_audit(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        baseline = _audit_login_failed_count(tmp_server_db)
        with pytest.raises(AuthFailedError):
            verify(tmp_server_db, "ghost", "any", params=fast_params)
        assert _audit_login_failed_count(tmp_server_db) == baseline

    def test_bad_password_writes_no_audit(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        _insert_first_admin(
            tmp_server_db, "admin", "pw",
            params=fast_params, os_user="host",
        )
        baseline = _audit_login_failed_count(tmp_server_db)
        with pytest.raises(AuthFailedError) as exc_info:
            verify(tmp_server_db, "admin", "wrong", params=fast_params)
        assert exc_info.value.cause == AuthFailureCause.BAD_PASSWORD
        assert _audit_login_failed_count(tmp_server_db) == baseline

    def test_disabled_writes_no_audit(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        _insert_first_admin(
            tmp_server_db, "admin", "pw",
            params=fast_params, os_user="host",
        )
        tmp_server_db.execute(
            "UPDATE users SET disabled = 1 WHERE user_id = 'admin'"
        )
        tmp_server_db.commit()

        baseline = _audit_login_failed_count(tmp_server_db)
        with pytest.raises(AuthFailedError) as exc_info:
            verify(tmp_server_db, "admin", "pw", params=fast_params)
        assert exc_info.value.cause == AuthFailureCause.DISABLED
        assert _audit_login_failed_count(tmp_server_db) == baseline


class TestVerifySuccessAlsoSilent:
    """verify() success path also writes no audit. The success path's
    audit (EVT_LOGIN) is emitted by login(), not verify()."""

    def test_success_writes_no_login_audit(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        _insert_first_admin(
            tmp_server_db, "admin", "pw",
            params=fast_params, os_user="host",
        )
        baseline_login = tmp_server_db.execute(
            "SELECT COUNT(*) FROM audit WHERE event = ?", ("EVT_LOGIN",)
        ).fetchone()[0]
        user = verify(tmp_server_db, "admin", "pw", params=fast_params)
        assert user.user_id == "admin"
        new_login = tmp_server_db.execute(
            "SELECT COUNT(*) FROM audit WHERE event = ?", ("EVT_LOGIN",)
        ).fetchone()[0]
        assert new_login == baseline_login
