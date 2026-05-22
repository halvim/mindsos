"""
Phase 22 — capability-gate denial across all six admin verbs.

ADR-0013 §Decision: "Every privileged endpoint audits both its happy
path and its denial path." Each P22 verb routes through
:func:`_require_or_audit` (Phase 21 PB-6); on denial it writes
``EVT_PERMISSION_DENIED`` with ``extra = {"capability": <CAP>, "verb":
<verb>}`` per Phase 21 PB-13 and raises :class:`PermissionDeniedError`.

This file consolidates the "non-admin caller is denied" path for all
six verbs to keep the per-verb test files focused on happy-path +
domain errors.
"""

from __future__ import annotations

import json

import pytest

from mindsos_server.admin import (
    admin_demote_user,
    admin_disable_user,
    admin_enable_user,
    admin_kill_session,
    admin_promote_user,
    hard_delete_user,
)
from mindsos_server.audit import EVT_PERMISSION_DENIED
from mindsos_server.capabilities import (
    CAN_HARD_DELETE_ARCHIVED,
    CAN_KILL_SESSION,
    CAN_MANAGE_USERS,
)
from mindsos_server.errors import PermissionDeniedError


_VERBS = [
    ("admin_promote_user", admin_promote_user, "alice",
     {"target_user_id": "alice"}, CAN_MANAGE_USERS),
    ("admin_demote_user", admin_demote_user, "admin2",
     {"target_user_id": "admin2"}, CAN_MANAGE_USERS),
    ("admin_disable_user", admin_disable_user, "alice",
     {"target_user_id": "alice"}, CAN_MANAGE_USERS),
    ("admin_enable_user", admin_enable_user, "alice",
     {"target_user_id": "alice"}, CAN_MANAGE_USERS),
    ("admin_kill_session", admin_kill_session, None,
     {"target_session_id": "any"}, CAN_KILL_SESSION),
    ("hard_delete_user", hard_delete_user, "alice",
     {"target_user_id": "alice"}, CAN_HARD_DELETE_ARCHIVED),
]


@pytest.mark.parametrize(
    "verb_name,verb_fn,_target,kwargs,expected_cap", _VERBS
)
class TestNonAdminDenied:
    def test_raises_permission_denied(
        self, verb_name, verb_fn, _target, kwargs, expected_cap,
        seeded_two_admins, seeded_user, non_admin_session
    ):
        # Use the appropriate seed; for tests we just need denial which
        # happens BEFORE target lookup.
        conn = seeded_user  # seeded_user has both 'admin' + 'alice'; 'admin2' missing
        with pytest.raises(PermissionDeniedError) as exc_info:
            verb_fn(conn, non_admin_session, **kwargs)
        assert exc_info.value.capability == expected_cap

    def test_evt_permission_denied_emitted(
        self, verb_name, verb_fn, _target, kwargs, expected_cap,
        seeded_two_admins, seeded_user, non_admin_session
    ):
        conn = seeded_user
        with pytest.raises(PermissionDeniedError):
            verb_fn(conn, non_admin_session, **kwargs)
        rows = conn.execute(
            "SELECT actor_user, extra_json FROM audit WHERE event = ?",
            (EVT_PERMISSION_DENIED,),
        ).fetchall()
        assert len(rows) == 1
        actor, extra_json = rows[0]
        assert actor == "alice-caller"
        extra = json.loads(extra_json)
        # Phase 21 PB-13 payload
        assert extra["capability"] == expected_cap
        assert extra["verb"] == verb_name
