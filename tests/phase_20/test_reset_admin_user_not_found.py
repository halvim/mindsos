"""
Phase 20 reset_admin() target-validation: UserNotFoundError on missing user_id.

Per Phase 20 PB-A: reset-admin requires existing target. New-admin
path is bootstrap (P18) / admin_promote_user (P22). Reset-admin will
NEVER mint admin rows from scratch.

Per Phase 20 PB-O: distinct exception class (`UserNotFoundError`),
not `AuthFailedError(UNKNOWN_USER)` — reset-admin attempts no auth.
"""

from __future__ import annotations

import pytest

from mindsos_server.admin import reset_admin
from mindsos_server.audit import EVT_KILL_SESSION, EVT_RESET_ADMIN
from mindsos_server.errors import UserNotFoundError


class TestUserNotFound:
    def test_raises_user_not_found_error(
        self, tmp_server_db, fast_params
    ) -> None:
        with pytest.raises(UserNotFoundError) as exc_info:
            reset_admin(
                tmp_server_db,
                "ghost",
                "newpw",
                os_user="test-host",
                params=fast_params,
            )
        assert exc_info.value.target_user_id == "ghost"

    def test_error_message_includes_user_id(
        self, tmp_server_db, fast_params
    ) -> None:
        with pytest.raises(UserNotFoundError) as exc_info:
            reset_admin(
                tmp_server_db,
                "ghost",
                "newpw",
                os_user="test-host",
                params=fast_params,
            )
        assert "ghost" in str(exc_info.value)

    def test_no_users_row_created(
        self, tmp_server_db, fast_params
    ) -> None:
        with pytest.raises(UserNotFoundError):
            reset_admin(
                tmp_server_db,
                "ghost",
                "newpw",
                os_user="test-host",
                params=fast_params,
            )
        rows = tmp_server_db.execute(
            "SELECT user_id FROM users WHERE user_id = 'ghost'"
        ).fetchall()
        # PB-A — reset-admin NEVER mints new users.
        assert rows == []

    def test_no_audit_rows_written_on_failure(
        self, tmp_server_db, fast_params
    ) -> None:
        with pytest.raises(UserNotFoundError):
            reset_admin(
                tmp_server_db,
                "ghost",
                "newpw",
                os_user="test-host",
                params=fast_params,
            )
        # Neither summary nor session-kill events fire on validation failure.
        for event in (EVT_RESET_ADMIN, EVT_KILL_SESSION):
            rows = tmp_server_db.execute(
                "SELECT id FROM audit WHERE event = ?", (event,)
            ).fetchall()
            assert rows == [], f"unexpected {event} audit row"

    def test_other_users_unaffected(
        self, seeded_admin, fast_params
    ) -> None:
        old_hash = seeded_admin.execute(
            "SELECT password_hash FROM users WHERE user_id = 'admin'"
        ).fetchone()[0]
        with pytest.raises(UserNotFoundError):
            reset_admin(
                seeded_admin,
                "ghost",
                "newpw",
                os_user="test-host",
                params=fast_params,
            )
        new_hash = seeded_admin.execute(
            "SELECT password_hash FROM users WHERE user_id = 'admin'"
        ).fetchone()[0]
        assert old_hash == new_hash  # untouched
