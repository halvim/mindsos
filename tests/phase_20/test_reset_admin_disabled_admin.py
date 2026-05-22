"""
Phase 20 reset_admin() disabled-target handling.

Per Phase 20 PB-U: when target is `disabled=1`, reset-admin re-enables
the row AND fires a separate `EVT_ADMIN_ENABLE_USER` audit event in
addition to the summary `EVT_RESET_ADMIN`. First-fire of
`EVT_ADMIN_ENABLE_USER` shifts P22 → P20 (Phase 18 declared the
constant per PB-34; Phase 22 admin_enable_user is the second consumer).

Per PB-BB: the EVT_RESET_ADMIN extra_json's `was_disabled` field
denormalizes the prior state for the P21 audit reader.
"""

from __future__ import annotations

import json

from mindsos_server.admin import reset_admin
from mindsos_server.audit import EVT_ADMIN_ENABLE_USER, EVT_RESET_ADMIN


class TestDisabledAdminReEnabled:
    def test_disabled_column_set_to_zero(
        self, seeded_disabled_admin, fast_params
    ) -> None:
        # Sanity check: fixture put it at 1.
        before = seeded_disabled_admin.execute(
            "SELECT disabled FROM users WHERE user_id = 'admin'"
        ).fetchone()[0]
        assert int(before) == 1

        reset_admin(
            seeded_disabled_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )

        after = seeded_disabled_admin.execute(
            "SELECT disabled FROM users WHERE user_id = 'admin'"
        ).fetchone()[0]
        assert int(after) == 0

    def test_was_disabled_field_true(
        self, seeded_disabled_admin, fast_params
    ) -> None:
        result = reset_admin(
            seeded_disabled_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        assert result.was_disabled is True

    def test_evt_admin_enable_user_fires(
        self, seeded_disabled_admin, fast_params
    ) -> None:
        reset_admin(
            seeded_disabled_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        rows = seeded_disabled_admin.execute(
            "SELECT extra_json, target_user FROM audit WHERE event = ?",
            (EVT_ADMIN_ENABLE_USER,),
        ).fetchall()
        assert len(rows) == 1
        extra, target = rows[0]
        decoded = json.loads(extra)
        assert decoded == {"context": "reset_admin"}
        assert target == "admin"

    def test_evt_reset_admin_was_disabled_true(
        self, seeded_disabled_admin, fast_params
    ) -> None:
        reset_admin(
            seeded_disabled_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        row = seeded_disabled_admin.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_RESET_ADMIN,),
        ).fetchone()
        decoded = json.loads(row[0])
        assert decoded["was_disabled"] is True


class TestNotDisabledAdmin:
    """Inverse — non-disabled admin path does NOT fire EVT_ADMIN_ENABLE_USER."""

    def test_no_evt_admin_enable_user_when_already_enabled(
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
            "SELECT id FROM audit WHERE event = ?",
            (EVT_ADMIN_ENABLE_USER,),
        ).fetchall()
        assert rows == []
