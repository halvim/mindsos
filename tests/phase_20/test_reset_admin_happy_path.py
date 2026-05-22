"""
Phase 20 reset_admin() happy-path tests.

Verifies the basic-success case (existing enabled admin, zero
sessions): row's password_hash rotates to a new value, disabled stays
0, was_disabled returned as False, sessions_killed=0, three audit
events do NOT fire (no EVT_KILL_SESSION since N=0; no
EVT_ADMIN_ENABLE_USER since not disabled). The summary
EVT_RESET_ADMIN DOES fire.

Per ADR-0012 §am2 + Phase 20 PB-A + PB-C + PB-D + PB-R + PB-BB.
"""

from __future__ import annotations

import json

from mindsos_server.admin import ResetAdminResult, reset_admin
from mindsos_server.audit import (
    EVT_ADMIN_ENABLE_USER,
    EVT_KILL_SESSION,
    EVT_RESET_ADMIN,
)


class TestHappyPath:
    def test_returns_reset_admin_result(
        self, seeded_admin, fast_params
    ) -> None:
        result = reset_admin(
            seeded_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        assert isinstance(result, ResetAdminResult)
        assert result.user_id == "admin"
        assert result.sessions_killed == 0
        assert result.was_disabled is False

    def test_password_hash_rotated(self, seeded_admin, fast_params) -> None:
        old_hash = seeded_admin.execute(
            "SELECT password_hash FROM users WHERE user_id = 'admin'"
        ).fetchone()[0]
        reset_admin(
            seeded_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        new_hash = seeded_admin.execute(
            "SELECT password_hash FROM users WHERE user_id = 'admin'"
        ).fetchone()[0]
        assert old_hash != new_hash
        # Both are still argon2id-formatted (start with $argon2id$).
        assert new_hash.startswith("$argon2id$")

    def test_disabled_stays_zero_when_not_disabled(
        self, seeded_admin, fast_params
    ) -> None:
        reset_admin(
            seeded_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        disabled = seeded_admin.execute(
            "SELECT disabled FROM users WHERE user_id = 'admin'"
        ).fetchone()[0]
        assert int(disabled) == 0

    def test_actor_role_stays_admin(
        self, seeded_admin, fast_params
    ) -> None:
        reset_admin(
            seeded_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        actor_role = seeded_admin.execute(
            "SELECT actor_role FROM users WHERE user_id = 'admin'"
        ).fetchone()[0]
        assert actor_role == "admin"

    def test_evt_reset_admin_fires_once(
        self, seeded_admin, fast_params
    ) -> None:
        reset_admin(
            seeded_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        rows = seeded_admin.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_RESET_ADMIN,),
        ).fetchall()
        assert len(rows) == 1
        # PB-BB extra_json shape.
        decoded = json.loads(rows[0][0])
        assert decoded == {"was_disabled": False, "sessions_killed": 0}

    def test_no_evt_kill_session_when_zero_sessions(
        self, seeded_admin, fast_params
    ) -> None:
        reset_admin(
            seeded_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        rows = seeded_admin.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_KILL_SESSION,),
        ).fetchall()
        assert rows == []

    def test_no_evt_admin_enable_user_when_not_disabled(
        self, seeded_admin, fast_params
    ) -> None:
        reset_admin(
            seeded_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        rows = seeded_admin.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_ADMIN_ENABLE_USER,),
        ).fetchall()
        assert rows == []
