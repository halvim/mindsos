"""
Shared fixtures for Phase 18 tests.

Provides:

* :func:`tmp_server_db` — tmp-path SQLite DB opened with Phase 18 PB-19
  pragmas + migrated to v1. Yields the connection.
* :func:`fast_params` — :data:`mindsos_server._argon2._TEST_FAST_PARAMS`
  alias so individual tests don't have to import the underscore-prefixed
  constant.

Future phases (19-22) should mirror this conftest pattern for their own
phase test trees.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from mindsos_server._argon2 import _TEST_FAST_PARAMS, Argon2Params
from mindsos_server._db import open_db
from mindsos_server._schema import init_or_migrate


@pytest.fixture()
def fast_params() -> Argon2Params:
    """Low-cost argon2 params for tests per Phase 18 PB-14."""
    return _TEST_FAST_PARAMS


@pytest.fixture()
def tmp_server_db_path(tmp_path: Path) -> Path:
    """Path to a tmp ``server.db`` (file doesn't exist yet)."""
    return tmp_path / "server.db"


@pytest.fixture()
def tmp_server_db(tmp_server_db_path: Path) -> Iterator:
    """
    Open a fresh ``server.db`` at a tmp path, migrate to v1, yield the
    connection. Closes on teardown via the open_db context manager.
    """
    with open_db(tmp_server_db_path) as conn:
        init_or_migrate(conn)
        yield conn
