"""
Phase 20 reset_admin() target-validation: NotAnAdminError on non-admin target.

Per Phase 20 PB-E: reset-admin will NEVER escalate a non-admin user
to admin. That path is admin_promote_user (Phase 22), gated by
CAN_MANAGE_USERS. Without this guard, reset-admin would double as a
"promote arbitrary user to admin" backdoor for any operator with
filesystem access to server.db.

Per Phase 20 PB-N: exception carries (target_user_id, actual_role)
for informative error messages. Filesystem-access threat model has
no enumeration concern.
"""

from __future__ import annotations

import pytest

from mindsos_server.admin import reset_admin
from mindsos_server.audit import EVT_KILL_SESSION, EVT_RESET_ADMIN
from mindsos_server.errors import NotAnAdminError


class TestNotAnAdmin:
    def test_raises_not_an_admin_error(
        self, seeded_user, fast_params
    ) -> None:
        with pytest.raises(NotAnAdminError) as exc_info:
            reset_admin(
                seeded_user,
                "alice",
                "newpw",
                os_user="test-host",
                params=fast_params,
            )
        assert exc_info.value.target_user_id == "alice"
        assert exc_info.value.actual_role == "user"

    def test_error_message_includes_user_id_and_role(
        self, seeded_user, fast_params
    ) -> None:
        with pytest.raises(NotAnAdminError) as exc_info:
            reset_admin(
                seeded_user,
                "alice",
                "newpw",
                os_user="test-host",
                params=fast_params,
            )
        msg = str(exc_info.value)
        assert "alice" in msg
        assert "user" in msg  # actual_role surfaced per PB-N

    def test_users_row_unchanged(
        self, seeded_user, fast_params
    ) -> None:
        old_hash = seeded_user.execute(
            "SELECT password_hash FROM users WHERE user_id = 'alice'"
        ).fetchone()[0]
        with pytest.raises(NotAnAdminError):
            reset_admin(
                seeded_user,
                "alice",
                "newpw",
                os_user="test-host",
                params=fast_params,
            )
        new_hash = seeded_user.execute(
            "SELECT password_hash FROM users WHERE user_id = 'alice'"
        ).fetchone()[0]
        assert old_hash == new_hash

    def test_actor_role_stays_user_not_silently_promoted(
        self, seeded_user, fast_params
    ) -> None:
        # PB-E core regression: reset-admin must NEVER silently promote.
        with pytest.raises(NotAnAdminError):
            reset_admin(
                seeded_user,
                "alice",
                "newpw",
                os_user="test-host",
                params=fast_params,
            )
        actor_role = seeded_user.execute(
            "SELECT actor_role FROM users WHERE user_id = 'alice'"
        ).fetchone()[0]
        assert actor_role == "user"

    def test_no_audit_rows_written_on_failure(
        self, seeded_user, fast_params
    ) -> None:
        with pytest.raises(NotAnAdminError):
            reset_admin(
                seeded_user,
                "alice",
                "newpw",
                os_user="test-host",
                params=fast_params,
            )
        for event in (EVT_RESET_ADMIN, EVT_KILL_SESSION):
            rows = seeded_user.execute(
                "SELECT id FROM audit WHERE event = ?", (event,)
            ).fetchall()
            assert rows == [], f"unexpected {event} audit row"
