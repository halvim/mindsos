"""
Phase 21 ``_require_or_audit`` wrapper unit tests.

Verifies happy-path silent return, denial-path EVT_PERMISSION_DENIED
audit write + commit + raise (PB-6 + PB-13). Tests the wrapper
directly (not via admin_query_audit) so denial semantics are
isolated.

Per ADR-0013 §am2 + Phase 21 PB-6 + PB-13 + PB-14.
"""

from __future__ import annotations

import json

import pytest

from mindsos_server.audit import EVT_PERMISSION_DENIED
from mindsos_server.authz import _require_or_audit
from mindsos_server.capabilities import (
    CAN_MANAGE_USERS,
    CAN_VIEW_AUDIT_LOG,
)
from mindsos_server.errors import PermissionDeniedError


class TestHappyPath:
    def test_returns_silently_when_capability_present(
        self, tmp_server_db, admin_session
    ) -> None:
        # Should not raise; returns None.
        result = _require_or_audit(
            tmp_server_db, admin_session,
            CAN_VIEW_AUDIT_LOG, verb="admin_query_audit",
        )
        assert result is None

    def test_no_audit_row_written_on_happy_path(
        self, tmp_server_db, admin_session
    ) -> None:
        _require_or_audit(
            tmp_server_db, admin_session,
            CAN_VIEW_AUDIT_LOG, verb="admin_query_audit",
        )
        count = tmp_server_db.execute(
            "SELECT COUNT(*) FROM audit WHERE event = ?",
            (EVT_PERMISSION_DENIED,),
        ).fetchone()[0]
        assert count == 0


class TestDenialPath:
    def test_raises_permission_denied_error(
        self, tmp_server_db, user_session
    ) -> None:
        with pytest.raises(PermissionDeniedError) as excinfo:
            _require_or_audit(
                tmp_server_db, user_session,
                CAN_VIEW_AUDIT_LOG, verb="admin_query_audit",
            )
        assert excinfo.value.target_user_id == "alice"
        assert excinfo.value.capability == CAN_VIEW_AUDIT_LOG

    def test_writes_evt_permission_denied(
        self, tmp_server_db, user_session
    ) -> None:
        with pytest.raises(PermissionDeniedError):
            _require_or_audit(
                tmp_server_db, user_session,
                CAN_VIEW_AUDIT_LOG, verb="admin_query_audit",
            )
        rows = tmp_server_db.execute(
            "SELECT actor_user, target_user, extra_json FROM audit "
            "WHERE event = ?",
            (EVT_PERMISSION_DENIED,),
        ).fetchall()
        assert len(rows) == 1
        actor, target, extra_json = rows[0]
        assert actor == "alice"
        assert target is None
        extra = json.loads(extra_json)
        # PB-13 payload shape.
        assert extra["capability"] == CAN_VIEW_AUDIT_LOG
        assert extra["verb"] == "admin_query_audit"

    def test_audit_committed_before_raise(
        self, tmp_server_db, user_session
    ) -> None:
        """ADR-0013 §Consequences: denial audit must survive even if
        the caller's outer tx rolls back. _require_or_audit commits
        the denial-path audit row internally."""
        try:
            _require_or_audit(
                tmp_server_db, user_session,
                CAN_VIEW_AUDIT_LOG, verb="admin_query_audit",
            )
        except PermissionDeniedError:
            pass
        # Simulate caller rollback after the raise.
        tmp_server_db.rollback()
        # Row should still be present.
        count = tmp_server_db.execute(
            "SELECT COUNT(*) FROM audit WHERE event = ?",
            (EVT_PERMISSION_DENIED,),
        ).fetchone()[0]
        assert count == 1

    def test_different_capability_recorded(
        self, tmp_server_db, user_session
    ) -> None:
        # Tests that the wrapper records WHICHEVER capability was
        # passed — generalizes beyond CAN_VIEW_AUDIT_LOG so Phase 22's
        # consumers (CAN_MANAGE_USERS, CAN_KILL_SESSION, etc.) work
        # the same way.
        with pytest.raises(PermissionDeniedError):
            _require_or_audit(
                tmp_server_db, user_session,
                CAN_MANAGE_USERS, verb="admin_promote_user",
            )
        row = tmp_server_db.execute(
            "SELECT extra_json FROM audit WHERE event = ? "
            "ORDER BY id DESC LIMIT 1",
            (EVT_PERMISSION_DENIED,),
        ).fetchone()
        extra = json.loads(row[0])
        assert extra["capability"] == CAN_MANAGE_USERS
        assert extra["verb"] == "admin_promote_user"
