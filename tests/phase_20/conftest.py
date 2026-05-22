"""
Shared fixtures for Phase 20 tests (mindsos_server.admin.reset_admin).

Mirrors :mod:`tests.phase_19.conftest` shape — fixtures are scoped to
this phase's directory; pytest does not auto-inherit from sibling
phase conftests, so we duplicate the seed fixtures here and add the
Phase 20-specific ones.

Phase 20 fixtures added on top of Phase 19's:

* :func:`seeded_disabled_admin` — admin row with ``disabled=1`` so
  reset-admin's PB-U conditional ``EVT_ADMIN_ENABLE_USER`` path can be
  exercised.
* :func:`seeded_admin_with_sessions` — admin row + N pre-existing
  session rows inserted directly via SQL (bypassing login's
  concurrent-login refusal). Drives the multi-session DELETE +
  per-row ``EVT_KILL_SESSION`` audit path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from mindsos_server._argon2 import _TEST_FAST_PARAMS, Argon2Params
from mindsos_server._db import open_db
from mindsos_server._schema import init_or_migrate
from mindsos_server.sessions import SessionTTL, _TEST_FAST_TTL
from mindsos_server.users import _insert_first_admin, insert_user


@pytest.fixture()
def fast_params() -> Argon2Params:
    """Low-cost argon2 params for tests per Phase 18 PB-14."""
    return _TEST_FAST_PARAMS


@pytest.fixture()
def fast_ttl() -> SessionTTL:
    """Test-fast TTL per Phase 19 PB-12 (1s sliding / 2s absolute)."""
    return _TEST_FAST_TTL


@pytest.fixture()
def tmp_server_db_path(tmp_path: Path) -> Path:
    """Path to a tmp ``server.db`` (file doesn't exist yet)."""
    return tmp_path / "server.db"


@pytest.fixture()
def tmp_server_db(tmp_server_db_path: Path) -> Iterator:
    """
    Open a fresh ``server.db`` at a tmp path, migrate to v2 (Phase 19
    schema includes the sessions table that Phase 20 reset-admin
    operates on), yield the connection.
    """
    with open_db(tmp_server_db_path) as conn:
        init_or_migrate(conn)
        yield conn


@pytest.fixture()
def seeded_admin(tmp_server_db, fast_params):
    """
    Pre-insert an admin user 'admin' with password 'adminpw'. The
    bootstrap helper writes one ``EVT_BOOTSTRAP`` audit row in setup;
    Phase 20 tests that count audit rows should account for the
    pre-existing row OR filter by event type.
    """
    _insert_first_admin(
        tmp_server_db,
        "admin",
        "adminpw",
        params=fast_params,
        os_user="test-host",
    )
    return tmp_server_db


@pytest.fixture()
def seeded_user(tmp_server_db, fast_params):
    """Pre-insert a regular non-admin user 'alice' with password 'alicepw'."""
    insert_user(
        tmp_server_db,
        "alice",
        "alicepw",
        actor_role="user",
        params=fast_params,
        audit_actor="test-host",
    )
    return tmp_server_db


@pytest.fixture()
def seeded_disabled_admin(seeded_admin):
    """
    Mutate the seeded admin row to ``disabled=1`` so reset-admin's
    PB-U disabled-target branch can be exercised. Returns the same
    connection.
    """
    seeded_admin.execute(
        "UPDATE users SET disabled = 1 WHERE user_id = 'admin'"
    )
    seeded_admin.commit()
    return seeded_admin


def _insert_extra_session(conn, user_id: str, suffix: str) -> str:
    """
    Insert a synthetic session row directly via SQL (bypasses login's
    refuse-concurrent-login check). Returns the inserted session_id.
    Mirrors the Phase 19 ``test_kill_my_own_sessions.py`` helper
    pattern.
    """
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
def seeded_admin_with_sessions(seeded_admin):
    """
    Seeded admin + 3 pre-existing sessions for that admin. Returns
    (conn, [session_id, ...]) tuple — tests index into the list to
    assert per-row EVT_KILL_SESSION emission.
    """
    session_ids = [
        _insert_extra_session(seeded_admin, "admin", suffix=str(i))
        for i in range(3)
    ]
    return seeded_admin, session_ids


@pytest.fixture()
def insert_extra_session():
    """Expose the helper to tests that need to inject sessions ad-hoc."""
    return _insert_extra_session
