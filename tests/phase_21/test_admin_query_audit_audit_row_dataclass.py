"""
Phase 21 :class:`AuditRow` dataclass shape tests.

Verifies that :class:`AuditRow` is frozen (immutable), that ``extra``
is a parsed Mapping (not a raw JSON string), and that null
actor/target survive the round-trip.

Per ADR-0013 §am2 + Phase 21 PB-9.
"""

from __future__ import annotations

import dataclasses

import pytest

from mindsos_server.admin import AuditRow, admin_query_audit


class TestFrozen:
    def test_audit_row_is_frozen_dataclass(self) -> None:
        # @dataclass(frozen=True) → AuditRow is a dataclass with
        # frozen=True (immutable).
        assert dataclasses.is_dataclass(AuditRow)
        # Frozen check: attempting to mutate raises.
        row = AuditRow(
            id=1, ts="2026-05-21T00:00:00.000Z",
            actor="alice", event="EVT_LOGIN", target=None,
            extra={"cause": "OK"},
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            row.id = 999  # type: ignore[misc]

    def test_audit_row_equality_by_fields(self) -> None:
        a = AuditRow(
            id=1, ts="2026-05-21T00:00:00.000Z",
            actor="alice", event="EVT_LOGIN", target=None, extra={},
        )
        b = AuditRow(
            id=1, ts="2026-05-21T00:00:00.000Z",
            actor="alice", event="EVT_LOGIN", target=None, extra={},
        )
        assert a == b


class TestExtraIsParsed:
    def test_extra_returned_as_mapping(
        self, tmp_server_db, admin_session, insert_audit_row
    ) -> None:
        insert_audit_row(
            "2026-05-21T00:00:00.000Z",
            actor="alice", event="EVT_LOGIN_FAILED",
            extra={"cause": "WRONG_PASSWORD"},
        )
        result = admin_query_audit(tmp_server_db, admin_session)
        login_failed = [r for r in result if r.event == "EVT_LOGIN_FAILED"]
        # Mapping accessor works without re-parsing.
        assert login_failed[0].extra["cause"] == "WRONG_PASSWORD"

    def test_empty_extra_becomes_empty_dict(
        self, tmp_server_db, admin_session, insert_audit_row
    ) -> None:
        # Insert with extra = '{}' (the DEFAULT TEXT column value).
        insert_audit_row(
            "2026-05-21T00:00:00.000Z",
            actor="alice", event="EVT_LOGIN", extra={},
        )
        result = admin_query_audit(tmp_server_db, admin_session)
        login_rows = [r for r in result if r.event == "EVT_LOGIN"]
        assert dict(login_rows[0].extra) == {}


class TestNullColumns:
    def test_actor_can_be_none(
        self, tmp_server_db, admin_session, insert_audit_row
    ) -> None:
        insert_audit_row(
            "2026-05-21T00:00:00.000Z",
            actor=None, event="EVT_LOGIN",
        )
        result = admin_query_audit(tmp_server_db, admin_session)
        login_rows = [r for r in result if r.event == "EVT_LOGIN"]
        assert login_rows[0].actor is None

    def test_target_can_be_none(
        self, tmp_server_db, admin_session, insert_audit_row
    ) -> None:
        insert_audit_row(
            "2026-05-21T00:00:00.000Z",
            actor="alice", event="EVT_LOGIN", target=None,
        )
        result = admin_query_audit(tmp_server_db, admin_session)
        login_rows = [r for r in result if r.event == "EVT_LOGIN"]
        assert login_rows[0].target is None
