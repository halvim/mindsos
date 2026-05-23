"""
Phase 22 R2 PB-16 — audit ``extra_json`` payload shapes for new events.

Locks each verb's extra payload at one place — protects against drift
between docstrings, README, ADR amendment text, and actual emission.
"""

from __future__ import annotations

import json

from mindsos_server.admin import (
    admin_demote_user,
    admin_disable_user,
    admin_enable_user,
    admin_promote_user,
    hard_delete_user,
)
from mindsos_server.audit import (
    EVT_ADMIN_DEMOTE_USER,
    EVT_ADMIN_DISABLE_USER,
    EVT_ADMIN_ENABLE_USER,
    EVT_ADMIN_PROMOTE_USER,
    EVT_HARD_DELETE_USER,
)


def _read_extra(conn, event: str) -> dict:
    rows = conn.execute(
        "SELECT extra_json FROM audit WHERE event = ?", (event,)
    ).fetchall()
    assert len(rows) == 1, f"expected one {event} row, got {len(rows)}"
    return json.loads(rows[0][0])


class TestPromoteUserExtra:
    def test_shape(self, seeded_user, admin_session):
        admin_promote_user(seeded_user, admin_session, target_user_id="alice")
        extra = _read_extra(seeded_user, EVT_ADMIN_PROMOTE_USER)
        assert extra == {"prior_role": "user"}


class TestDemoteUserExtra:
    def test_shape(self, seeded_admin_target_with_sessions, admin_session):
        conn, session_ids = seeded_admin_target_with_sessions
        admin_demote_user(conn, admin_session, target_user_id="admin2")
        extra = _read_extra(conn, EVT_ADMIN_DEMOTE_USER)
        assert extra == {
            "prior_role": "admin",
            "sessions_killed": len(session_ids),
        }


class TestDisableUserExtra:
    def test_active_target(self, seeded_user_with_sessions, admin_session):
        conn, session_ids = seeded_user_with_sessions
        admin_disable_user(conn, admin_session, target_user_id="alice")
        extra = _read_extra(conn, EVT_ADMIN_DISABLE_USER)
        assert extra == {
            "was_already_disabled": False,
            "sessions_killed": len(session_ids),
        }

    def test_already_disabled(self, seeded_disabled_user, admin_session):
        admin_disable_user(
            seeded_disabled_user, admin_session, target_user_id="alice"
        )
        extra = _read_extra(seeded_disabled_user, EVT_ADMIN_DISABLE_USER)
        assert extra == {
            "was_already_disabled": True,
            "sessions_killed": 0,
        }


class TestEnableUserExtra:
    def test_active_to_active(self, seeded_user, admin_session):
        admin_enable_user(seeded_user, admin_session, target_user_id="alice")
        extra = _read_extra(seeded_user, EVT_ADMIN_ENABLE_USER)
        assert extra == {"was_already_enabled": True}

    def test_disabled_to_enabled(self, seeded_disabled_user, admin_session):
        admin_enable_user(
            seeded_disabled_user, admin_session, target_user_id="alice"
        )
        extra = _read_extra(seeded_disabled_user, EVT_ADMIN_ENABLE_USER)
        assert extra == {"was_already_enabled": False}


class TestHardDeleteUserExtra:
    # Phase 25 PB-39 + ADR-0013 §am3 — extra_json gains additive
    # ``local_dump_existed: bool`` key. The default when persister=None
    # (the Phase 22 call sites which never pass persister) is False.
    def test_active_user(self, seeded_user_with_sessions, admin_session):
        conn, session_ids = seeded_user_with_sessions
        hard_delete_user(conn, admin_session, target_user_id="alice")
        extra = _read_extra(conn, EVT_HARD_DELETE_USER)
        assert extra == {
            "prior_role": "user",
            "was_disabled": False,
            "sessions_killed": len(session_ids),
            "local_dump_existed": False,
        }

    def test_disabled_admin(self, seeded_disabled_admin_extra, admin_session):
        hard_delete_user(
            seeded_disabled_admin_extra,
            admin_session,
            target_user_id="admin2",
        )
        extra = _read_extra(
            seeded_disabled_admin_extra, EVT_HARD_DELETE_USER
        )
        assert extra == {
            "prior_role": "admin",
            "was_disabled": True,
            "sessions_killed": 0,
            "local_dump_existed": False,
        }
