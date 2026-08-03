"""
Shared fixtures for Phase 22 tests (admin verbs + helpers).

Extends the Phase 20 conftest shape. Adds:

* :func:`admin_session` — Phase 21-style ``Session.for_testing`` shim
  with ``ADMIN_CAPS``; the canonical caller for happy-path tests.
* :func:`non_admin_session` — same shim, carrying ``USER_CAPS``;
  capability-denial tests.
* :func:`seeded_two_admins` — two admin rows ('admin', 'admin2'); lets
  demote/disable/hard-delete tests target one while keeping
  ``_assert_not_sole_admin`` invariant satisfied.
* :func:`seeded_admin_target_with_sessions` — 'admin2' admin row +
  pre-existing sessions for that admin (synthetic via SQL); drives
  the per-row ``EVT_KILL_SESSION`` audit emission tests.
* :func:`seeded_user_with_sessions` — 'alice' user + N synthetic
  sessions; drives disable / hard-delete path tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from mindsos_server._argon2 import _TEST_FAST_PARAMS, Argon2Params
from mindsos_server._db import open_db
from mindsos_server._schema import init_or_migrate
from mindsos_server.session import Session
from mindsos_server.sessions import SessionTTL, _TEST_FAST_TTL
from mindsos_server.users import _insert_first_admin, insert_user


@pytest.fixture()
def fast_params() -> Argon2Params:
    """Low-cost argon2 params for tests per Phase 18 PB-14."""
    return _TEST_FAST_PARAMS


@pytest.fixture()
def fast_ttl() -> SessionTTL:
    return _TEST_FAST_TTL


@pytest.fixture()
def tmp_server_db_path(tmp_path: Path) -> Path:
    return tmp_path / "server.db"


@pytest.fixture()
def tmp_server_db(tmp_server_db_path: Path) -> Iterator:
    with open_db(tmp_server_db_path) as conn:
        init_or_migrate(conn)
        yield conn


@pytest.fixture()
def admin_session() -> Session:
    """Caller session with ADMIN_CAPS (passes _require_or_audit for all P22 caps)."""
    return Session.for_testing("admin-caller", is_admin=True)


@pytest.fixture()
def non_admin_session() -> Session:
    """Caller session with ``USER_CAPS`` — denied on every P22 cap.

    ``USER_CAPS`` is no longer empty — CORE-C2R1 / ADR-0002 §am-3
    added the two skill-lifecycle capabilities — but it holds none
    of the capabilities under test here, so the denial paths are
    unaffected.
    """
    return Session.for_testing("alice-caller", is_admin=False)


def _insert_extra_session(conn, user_id: str, suffix: str) -> str:
    ts = "2026-05-21T00:00:00.000Z"
    session_id = f"sess-{user_id}-{suffix}"
    conn.execute(
        "INSERT INTO sessions "
        "(session_id, user_id, token_hash, created_at, last_seen_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (session_id, user_id, f"hash-{user_id}-{suffix}", ts, ts),
    )
    conn.commit()
    return session_id


@pytest.fixture()
def insert_extra_session():
    return _insert_extra_session


@pytest.fixture()
def seeded_admin(tmp_server_db, fast_params):
    """One admin 'admin'."""
    _insert_first_admin(
        tmp_server_db, "admin", "adminpw",
        params=fast_params, os_user="test-host",
    )
    return tmp_server_db


@pytest.fixture()
def seeded_two_admins(seeded_admin, fast_params):
    """Two admins: 'admin' + 'admin2'."""
    insert_user(
        seeded_admin, "admin2", "admin2pw",
        actor_role="admin", params=fast_params, audit_actor="test-host",
    )
    return seeded_admin


@pytest.fixture()
def seeded_user(seeded_admin, fast_params):
    """Admin 'admin' + user 'alice'."""
    insert_user(
        seeded_admin, "alice", "alicepw",
        actor_role="user", params=fast_params, audit_actor="test-host",
    )
    return seeded_admin


@pytest.fixture()
def seeded_user_with_sessions(seeded_user):
    """User 'alice' + 3 synthetic sessions."""
    session_ids = [
        _insert_extra_session(seeded_user, "alice", suffix=str(i))
        for i in range(3)
    ]
    return seeded_user, session_ids


@pytest.fixture()
def seeded_admin_target_with_sessions(seeded_two_admins):
    """Admin 'admin2' + 2 synthetic sessions for that admin."""
    session_ids = [
        _insert_extra_session(seeded_two_admins, "admin2", suffix=str(i))
        for i in range(2)
    ]
    return seeded_two_admins, session_ids


@pytest.fixture()
def seeded_disabled_user(seeded_user):
    """User 'alice' with disabled=1."""
    seeded_user.execute("UPDATE users SET disabled = 1 WHERE user_id = 'alice'")
    seeded_user.commit()
    return seeded_user


@pytest.fixture()
def seeded_disabled_admin_extra(seeded_two_admins):
    """Two admins; 'admin2' is disabled=1, 'admin' is active."""
    seeded_two_admins.execute(
        "UPDATE users SET disabled = 1 WHERE user_id = 'admin2'"
    )
    seeded_two_admins.commit()
    return seeded_two_admins
