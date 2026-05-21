"""
Tests for ``mindsos_server.audit`` — Phase 18 PB-34 + PB-35.
"""

from __future__ import annotations

import json
import re

from mindsos_server.audit import (
    ALL_AUDIT_EVENTS,
    EVT_ADMIN_CREATE_USER,
    EVT_BOOTSTRAP,
    EVT_LOGIN,
    EVT_LOGIN_FAILED,
    EVT_PERMISSION_DENIED,
    _now_utc_iso,
    write_audit,
)


class TestFullEnumPerPB34:
    """PB-34 — full ADR-0013 enum shipped at Phase 18."""

    def test_login_constants_present(self) -> None:
        assert EVT_LOGIN in ALL_AUDIT_EVENTS
        assert EVT_LOGIN_FAILED in ALL_AUDIT_EVENTS

    def test_authz_constants_present(self) -> None:
        assert EVT_PERMISSION_DENIED in ALL_AUDIT_EVENTS

    def test_user_mgmt_constants_present(self) -> None:
        assert EVT_ADMIN_CREATE_USER in ALL_AUDIT_EVENTS

    def test_bootstrap_constants_present(self) -> None:
        assert EVT_BOOTSTRAP in ALL_AUDIT_EVENTS

    def test_all_constants_unique(self) -> None:
        assert len(ALL_AUDIT_EVENTS) == len(set(ALL_AUDIT_EVENTS))

    def test_all_constants_have_evt_prefix(self) -> None:
        for evt in ALL_AUDIT_EVENTS:
            assert evt.startswith("EVT_"), f"audit event missing EVT_ prefix: {evt!r}"


class TestNowUtcIso:
    """PB-35 — TEXT ISO-8601 UTC ms format, Z-suffixed."""

    def test_format_regex(self) -> None:
        ts = _now_utc_iso()
        # YYYY-MM-DDTHH:MM:SS.mmmZ
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", ts), \
            f"timestamp shape wrong: {ts!r}"

    def test_lex_sortable(self) -> None:
        import time
        t1 = _now_utc_iso()
        time.sleep(0.01)
        t2 = _now_utc_iso()
        assert t1 < t2, "ISO-8601 timestamps must lex-sort chronologically"


class TestWriteAudit:
    """write_audit row shape + JSON serialization."""

    def test_basic_write(self, tmp_server_db) -> None:
        write_audit(
            tmp_server_db,
            actor="alice",
            event=EVT_LOGIN,
            target=None,
            extra=None,
        )
        tmp_server_db.commit()
        rows = tmp_server_db.execute(
            "SELECT actor_user, event, target_user, extra_json FROM audit"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0] == ("alice", EVT_LOGIN, None, "{}")

    def test_extra_json_serialized(self, tmp_server_db) -> None:
        write_audit(
            tmp_server_db,
            actor="alice",
            event=EVT_LOGIN_FAILED,
            target="alice",
            extra={"cause": "BAD_PASSWORD", "attempts": 3},
        )
        tmp_server_db.commit()
        row = tmp_server_db.execute(
            "SELECT extra_json FROM audit WHERE event=?", (EVT_LOGIN_FAILED,)
        ).fetchone()
        decoded = json.loads(row[0])
        assert decoded == {"cause": "BAD_PASSWORD", "attempts": 3}

    def test_ts_column_iso_format(self, tmp_server_db) -> None:
        write_audit(
            tmp_server_db, actor="alice", event=EVT_LOGIN, target=None, extra=None
        )
        tmp_server_db.commit()
        ts = tmp_server_db.execute("SELECT ts FROM audit").fetchone()[0]
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", ts)

    def test_does_not_auto_commit(self, tmp_server_db) -> None:
        """write_audit doesn't commit per ADR-0013 (caller controls txn)."""
        write_audit(
            tmp_server_db, actor="alice", event=EVT_LOGIN, target=None, extra=None
        )
        # WITHOUT a commit, the row should still be visible to the same conn
        # (DEFERRED isolation) but rollback would discard.
        tmp_server_db.rollback()
        rows = tmp_server_db.execute("SELECT COUNT(*) FROM audit").fetchone()
        assert rows[0] == 0, "rollback should discard uncommitted audit row"

    def test_actor_nullable_for_system_events(self, tmp_server_db) -> None:
        """actor=None allowed for future system-actor events."""
        write_audit(
            tmp_server_db, actor=None, event=EVT_LOGIN, target=None, extra=None
        )
        tmp_server_db.commit()
        row = tmp_server_db.execute(
            "SELECT actor_user FROM audit"
        ).fetchone()
        assert row[0] is None
