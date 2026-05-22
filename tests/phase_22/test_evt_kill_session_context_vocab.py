"""
Phase 22 R2 PB-14 — EVT_KILL_SESSION.extra.context vocabulary lock.

Four context strings (in addition to Phase 19's "kill_my_own_sessions"
+ Phase 20's "reset_admin"): admin_kill_session, admin_disable_user,
admin_demote_user, hard_delete_user. Grep-able verbatim strings.
"""

from __future__ import annotations

import json

from mindsos_server.admin import (
    admin_demote_user,
    admin_disable_user,
    admin_kill_session,
    hard_delete_user,
)
from mindsos_server.audit import EVT_KILL_SESSION


def _contexts(conn) -> list[str]:
    rows = conn.execute(
        "SELECT extra_json FROM audit WHERE event = ?",
        (EVT_KILL_SESSION,),
    ).fetchall()
    return [json.loads(r[0])["context"] for r in rows]


def test_admin_kill_session_context(seeded_user_with_sessions, admin_session):
    conn, session_ids = seeded_user_with_sessions
    admin_kill_session(
        conn, admin_session, target_session_id=session_ids[0]
    )
    assert _contexts(conn) == ["admin_kill_session"]


def test_admin_disable_user_context(
    seeded_user_with_sessions, admin_session
):
    conn, session_ids = seeded_user_with_sessions
    admin_disable_user(conn, admin_session, target_user_id="alice")
    contexts = _contexts(conn)
    assert len(contexts) == len(session_ids)
    assert all(c == "admin_disable_user" for c in contexts)


def test_admin_demote_user_context(
    seeded_admin_target_with_sessions, admin_session
):
    conn, session_ids = seeded_admin_target_with_sessions
    admin_demote_user(conn, admin_session, target_user_id="admin2")
    contexts = _contexts(conn)
    assert len(contexts) == len(session_ids)
    assert all(c == "admin_demote_user" for c in contexts)


def test_hard_delete_user_context(
    seeded_user_with_sessions, admin_session
):
    conn, session_ids = seeded_user_with_sessions
    hard_delete_user(conn, admin_session, target_user_id="alice")
    contexts = _contexts(conn)
    assert len(contexts) == len(session_ids)
    assert all(c == "hard_delete_user" for c in contexts)
