"""
Phase 21 capability-denial tests.

Verifies that callers without ``CAN_VIEW_AUDIT_LOG`` get
:class:`PermissionDeniedError` (PB-14) + an
:data:`EVT_PERMISSION_DENIED` audit row written + committed BEFORE
the raise (PB-13 + ADR-0013 §Decision "denial path audited").

Also verifies that the EVT_AUDIT_QUERY happy-path emission does NOT
fire on denial — the denial short-circuits the body.

Per ADR-0013 §am2 PB-6 + PB-13 + PB-14.
"""

from __future__ import annotations

import json

import pytest

from mindsos_server.admin import admin_query_audit
from mindsos_server.audit import EVT_AUDIT_QUERY, EVT_PERMISSION_DENIED
from mindsos_server.capabilities import CAN_VIEW_AUDIT_LOG
from mindsos_server.errors import PermissionDeniedError


class TestDenial:
    def test_non_admin_raises(
        self, tmp_server_db, user_session
    ) -> None:
        with pytest.raises(PermissionDeniedError):
            admin_query_audit(tmp_server_db, user_session)

    def test_permission_denied_error_carries_user_id_and_capability(
        self, tmp_server_db, user_session
    ) -> None:
        with pytest.raises(PermissionDeniedError) as excinfo:
            admin_query_audit(tmp_server_db, user_session)
        assert excinfo.value.target_user_id == "alice"
        assert excinfo.value.capability == CAN_VIEW_AUDIT_LOG

    def test_denial_writes_evt_permission_denied_row(
        self, tmp_server_db, user_session
    ) -> None:
        with pytest.raises(PermissionDeniedError):
            admin_query_audit(tmp_server_db, user_session)
        rows = tmp_server_db.execute(
            "SELECT actor_user, event, extra_json FROM audit "
            "WHERE event = ?",
            (EVT_PERMISSION_DENIED,),
        ).fetchall()
        assert len(rows) == 1
        actor, event, extra_json = rows[0]
        assert actor == "alice"
        assert event == EVT_PERMISSION_DENIED
        # PB-13 payload shape: {"capability": ..., "verb": ...}.
        extra = json.loads(extra_json)
        assert extra["capability"] == CAN_VIEW_AUDIT_LOG
        assert extra["verb"] == "admin_query_audit"

    def test_denial_does_not_emit_evt_audit_query(
        self, tmp_server_db, user_session
    ) -> None:
        with pytest.raises(PermissionDeniedError):
            admin_query_audit(tmp_server_db, user_session)
        rows = tmp_server_db.execute(
            "SELECT COUNT(*) FROM audit WHERE event = ?",
            (EVT_AUDIT_QUERY,),
        ).fetchone()
        # Short-circuit on denial: no happy-path emission.
        assert rows[0] == 0


class TestAuditorOnlyRoleSucceeds:
    """
    The capability-based design (ADR-0002) lets a non-admin session
    holding ONLY ``CAN_VIEW_AUDIT_LOG`` read audit rows. This is the
    "auditor role" pattern referenced in ADR-0002 §Rationale.
    """

    def test_auditor_can_read(
        self, tmp_server_db, auditor_only_session, seeded_audit_rows
    ) -> None:
        # Should not raise.
        result = admin_query_audit(tmp_server_db, auditor_only_session)
        # 8 seeded rows; self-emitted EVT_AUDIT_QUERY is written AFTER
        # the SELECT so it's NOT in this call's result.
        assert len(result) == 8

    def test_auditor_emits_evt_audit_query_with_own_user_id(
        self, tmp_server_db, auditor_only_session, seeded_audit_rows
    ) -> None:
        admin_query_audit(tmp_server_db, auditor_only_session)
        row = tmp_server_db.execute(
            "SELECT actor_user FROM audit WHERE event = ?",
            (EVT_AUDIT_QUERY,),
        ).fetchone()
        # actor_user is the session's user_id, not "admin".
        assert row[0] == "auditor"
