"""
Phase 20 reset_admin() session-kill semantics.

Per Phase 20 PB-D: 1× EVT_RESET_ADMIN + N× EVT_KILL_SESSION (the
constant already declared at Phase 18; first-fire lifts P22→P20).
Per PB-AA: each EVT_KILL_SESSION carries
``extra = {"session_id": sid, "context": "reset_admin"}``.
Per PB-BB: EVT_RESET_ADMIN extra_json denormalizes `sessions_killed: N`.
Per PB-R: single transaction; SELECT-then-DELETE order matches the
implementation's per-row audit pass.
"""

from __future__ import annotations

import json

from mindsos_server.admin import reset_admin
from mindsos_server.audit import EVT_KILL_SESSION, EVT_RESET_ADMIN


class TestZeroSessions:
    def test_sessions_killed_zero_when_none_exist(
        self, seeded_admin, fast_params
    ) -> None:
        result = reset_admin(
            seeded_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        assert result.sessions_killed == 0

    def test_zero_evt_kill_session_rows(
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
            "SELECT id FROM audit WHERE event = ?", (EVT_KILL_SESSION,)
        ).fetchall()
        assert rows == []


class TestSingleSession:
    def test_session_row_deleted(
        self, seeded_admin, insert_extra_session, fast_params
    ) -> None:
        sid = insert_extra_session(seeded_admin, "admin", suffix="solo")
        reset_admin(
            seeded_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        rows = seeded_admin.execute(
            "SELECT session_id FROM sessions WHERE user_id = 'admin'"
        ).fetchall()
        assert rows == []

    def test_one_evt_kill_session_with_correct_payload(
        self, seeded_admin, insert_extra_session, fast_params
    ) -> None:
        sid = insert_extra_session(seeded_admin, "admin", suffix="solo")
        reset_admin(
            seeded_admin,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        rows = seeded_admin.execute(
            "SELECT extra_json, target_user, actor_user FROM audit "
            "WHERE event = ?",
            (EVT_KILL_SESSION,),
        ).fetchall()
        assert len(rows) == 1
        extra, target, actor = rows[0]
        decoded = json.loads(extra)
        # PB-AA payload shape.
        assert decoded == {"session_id": sid, "context": "reset_admin"}
        assert target == "admin"
        assert actor == "test-host"  # OS-user pattern per ADR-0012


class TestMultiSession:
    def test_all_session_rows_deleted(
        self, seeded_admin_with_sessions, fast_params
    ) -> None:
        conn, _ = seeded_admin_with_sessions
        reset_admin(
            conn,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        rows = conn.execute(
            "SELECT session_id FROM sessions WHERE user_id = 'admin'"
        ).fetchall()
        assert rows == []

    def test_sessions_killed_count_matches(
        self, seeded_admin_with_sessions, fast_params
    ) -> None:
        conn, session_ids = seeded_admin_with_sessions
        result = reset_admin(
            conn,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        assert result.sessions_killed == len(session_ids) == 3

    def test_per_row_evt_kill_session(
        self, seeded_admin_with_sessions, fast_params
    ) -> None:
        conn, session_ids = seeded_admin_with_sessions
        reset_admin(
            conn,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        rows = conn.execute(
            "SELECT extra_json FROM audit WHERE event = ? "
            "ORDER BY id ASC",
            (EVT_KILL_SESSION,),
        ).fetchall()
        assert len(rows) == 3
        captured_session_ids = sorted(
            json.loads(r[0])["session_id"] for r in rows
        )
        assert captured_session_ids == sorted(session_ids)
        # Each row carries the reset_admin context discriminator.
        for r in rows:
            decoded = json.loads(r[0])
            assert decoded["context"] == "reset_admin"

    def test_evt_reset_admin_sessions_killed_denormalized(
        self, seeded_admin_with_sessions, fast_params
    ) -> None:
        # PB-BB: P21 audit reader can answer "how many sessions were
        # killed" without joining EVT_KILL_SESSION rows.
        conn, _ = seeded_admin_with_sessions
        reset_admin(
            conn,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )
        row = conn.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_RESET_ADMIN,),
        ).fetchone()
        decoded = json.loads(row[0])
        assert decoded["sessions_killed"] == 3


class TestOtherUsersSessionsUntouched:
    def test_only_target_user_sessions_deleted(
        self,
        seeded_admin_with_sessions,
        insert_extra_session,
        fast_params,
        seeded_user,  # noqa: ARG002 — same conn; seeded for the user_id FK
    ) -> None:
        conn, _ = seeded_admin_with_sessions
        # Inject a session for alice (the seeded non-admin user).
        alice_sid = insert_extra_session(conn, "alice", suffix="0")

        reset_admin(
            conn,
            "admin",
            "newpw",
            os_user="test-host",
            params=fast_params,
        )

        # alice's session survives.
        rows = conn.execute(
            "SELECT session_id FROM sessions WHERE user_id = 'alice'"
        ).fetchall()
        assert [r[0] for r in rows] == [alice_sid]
