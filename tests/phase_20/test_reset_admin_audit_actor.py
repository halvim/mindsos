"""
Phase 20 reset_admin() audit-actor format.

Per ADR-0012 §am2 + Phase 18 ``EVT_BOOTSTRAP`` precedent: ``actor`` on
every audit row written by reset-admin is the OS-user verbatim (no
"OS:" prefix; no ``extra.auth="filesystem"`` flavor).

Three audit rows can fire per reset (PB-D + PB-U + PB-BB):
* EVT_RESET_ADMIN (always)
* EVT_KILL_SESSION (one per killed session)
* EVT_ADMIN_ENABLE_USER (iff target was disabled)

All three carry actor = ``os_user`` kwarg passed by the function's
caller (the CLI verb passes ``pwd.getpwuid(os.getuid()).pw_name``;
direct callers pass arbitrary strings).
"""

from __future__ import annotations

from mindsos_server.admin import reset_admin
from mindsos_server.audit import (
    EVT_ADMIN_ENABLE_USER,
    EVT_KILL_SESSION,
    EVT_RESET_ADMIN,
)


class TestActorFormatOnAllEvents:
    def test_evt_reset_admin_actor_equals_os_user(
        self, seeded_admin, fast_params
    ) -> None:
        reset_admin(
            seeded_admin,
            "admin",
            "newpw",
            os_user="hal9000",
            params=fast_params,
        )
        row = seeded_admin.execute(
            "SELECT actor_user FROM audit WHERE event = ?",
            (EVT_RESET_ADMIN,),
        ).fetchone()
        assert row[0] == "hal9000"

    def test_evt_kill_session_actor_equals_os_user(
        self, seeded_admin_with_sessions, fast_params
    ) -> None:
        conn, _ = seeded_admin_with_sessions
        reset_admin(
            conn,
            "admin",
            "newpw",
            os_user="hal9000",
            params=fast_params,
        )
        rows = conn.execute(
            "SELECT actor_user FROM audit WHERE event = ?",
            (EVT_KILL_SESSION,),
        ).fetchall()
        assert len(rows) == 3
        # Every kill-session row carries the OS user, not the target user_id.
        for row in rows:
            assert row[0] == "hal9000"

    def test_evt_admin_enable_user_actor_equals_os_user(
        self, seeded_disabled_admin, fast_params
    ) -> None:
        reset_admin(
            seeded_disabled_admin,
            "admin",
            "newpw",
            os_user="hal9000",
            params=fast_params,
        )
        row = seeded_disabled_admin.execute(
            "SELECT actor_user FROM audit WHERE event = ?",
            (EVT_ADMIN_ENABLE_USER,),
        ).fetchone()
        assert row[0] == "hal9000"


class TestActorIsVerbatimNoPrefix:
    """
    Mirrors Phase 18 EVT_BOOTSTRAP shape exactly — no "OS:" / "os:"
    prefix; no separator decoration. ADR-0012 §am2 locks this format.
    """

    def test_no_prefix_in_actor_string(
        self, seeded_admin, fast_params
    ) -> None:
        reset_admin(
            seeded_admin,
            "admin",
            "newpw",
            os_user="alice",
            params=fast_params,
        )
        row = seeded_admin.execute(
            "SELECT actor_user FROM audit WHERE event = ?",
            (EVT_RESET_ADMIN,),
        ).fetchone()
        actor = row[0]
        assert actor == "alice"  # exact equality; no decoration
        assert not actor.startswith("OS:")
        assert not actor.startswith("os:")


class TestTargetIsAlwaysUserId:
    """target_user on every audit row is the reset target's user_id."""

    def test_evt_reset_admin_target_equals_user_id(
        self, seeded_admin, fast_params
    ) -> None:
        reset_admin(
            seeded_admin,
            "admin",
            "newpw",
            os_user="hal9000",
            params=fast_params,
        )
        row = seeded_admin.execute(
            "SELECT target_user FROM audit WHERE event = ?",
            (EVT_RESET_ADMIN,),
        ).fetchone()
        assert row[0] == "admin"

    def test_evt_kill_session_target_equals_user_id(
        self, seeded_admin_with_sessions, fast_params
    ) -> None:
        conn, _ = seeded_admin_with_sessions
        reset_admin(
            conn,
            "admin",
            "newpw",
            os_user="hal9000",
            params=fast_params,
        )
        rows = conn.execute(
            "SELECT target_user FROM audit WHERE event = ?",
            (EVT_KILL_SESSION,),
        ).fetchall()
        for row in rows:
            assert row[0] == "admin"
