"""
Shared fixtures for Phase 19 tests.

Mirrors :mod:`tests.phase_18.conftest` shape; adds:

* :func:`fast_ttl` — :data:`mindsos_server.sessions._TEST_FAST_TTL`
  (1s sliding / 2s absolute per Phase 19 PB-12). Tests pass this kwarg
  so the suite exercises both expiry paths within the pytest-suite
  latency budget.
* :func:`seeded_user` / :func:`seeded_admin` — convenience fixtures
  that insert a user before login-path tests. They use fast_params +
  the Phase 18 ``_insert_first_admin`` / ``insert_user`` helpers.
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
    schema includes the sessions table), yield the connection.
    """
    with open_db(tmp_server_db_path) as conn:
        init_or_migrate(conn)
        yield conn


@pytest.fixture()
def seeded_admin(tmp_server_db, fast_params):
    """Pre-insert an admin user 'admin' with password 'adminpw'."""
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
    """Pre-insert a regular user 'alice' with password 'alicepw'."""
    insert_user(
        tmp_server_db,
        "alice",
        "alicepw",
        actor_role="user",
        params=fast_params,
        audit_actor="test-host",
    )
    return tmp_server_db
