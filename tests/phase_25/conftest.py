"""
Shared fixtures for Phase 25 tests (cross-user-read substrate).

Per PB-R6-03 (Round 6 pre-impl re-analysis lock):

* Autouse fixture resets ``mindsos_server.orchestrator`` module-level
  state (``_installed_locals`` + ``_mutex_registry``) before every test
  — orchestrator owns the install path, but the registries are
  module-level and would bleed across tests without an explicit reset.
* ``kl`` fixture builds a fresh :class:`KnowledgeLayer.bootstrap` per
  test — matches the future server-startup pattern and avoids the
  ``AlreadyInstalledError`` desync that would surface if ``KL._locals``
  retained state from a prior test.
* ``persister`` fixture builds a fresh :class:`InMemoryLocalPersister`
  per test — matches the CLI per-command-process fresh-persister
  invariant at v1.
* ``seeded_admin`` fixture inserts an admin row via Phase 18's
  ``_insert_first_admin`` so the audit + FK gates align with
  production schema.

The conftest extends the Phase 22 conftest shape — same DB fixture
chain, plus the Phase 25 module-state reset + KL + persister fixtures.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from mindsos_knowledge import KnowledgeLayer

from mindsos_server._argon2 import _TEST_FAST_PARAMS, Argon2Params
from mindsos_server._db import open_db
from mindsos_server._schema import init_or_migrate
from mindsos_server.orchestrator import reset_state_for_tests
from mindsos_server.persistence import InMemoryLocalPersister
from mindsos_server.session import Session
from mindsos_server.users import _insert_first_admin, insert_user


@pytest.fixture(autouse=True)
def _reset_orchestrator_state() -> Iterator[None]:
    """
    Autouse — reset module-level orchestrator state.

    Both ``_installed_locals`` and ``_mutex_registry`` are reset so
    per-test isolation matches the per-CLI-invocation isolation
    invariant in production.
    """
    reset_state_for_tests()
    yield
    reset_state_for_tests()


@pytest.fixture()
def fast_params() -> Argon2Params:
    """Low-cost argon2 params per Phase 18 PB-14."""
    return _TEST_FAST_PARAMS


@pytest.fixture()
def tmp_server_db_path(tmp_path: Path) -> Path:
    return tmp_path / "server.db"


@pytest.fixture()
def tmp_server_db(tmp_server_db_path: Path) -> Iterator:
    with open_db(tmp_server_db_path) as conn:
        init_or_migrate(conn)
        yield conn


@pytest.fixture()
def kl() -> KnowledgeLayer:
    """Fresh KL per test (PB-R6-03)."""
    return KnowledgeLayer.bootstrap()


@pytest.fixture()
def persister() -> InMemoryLocalPersister:
    """Fresh InMemoryLocalPersister per test."""
    return InMemoryLocalPersister()


@pytest.fixture()
def admin_session() -> Session:
    """Caller with ADMIN_CAPS — passes _require_or_audit for all P25 caps."""
    return Session.for_testing("admin-caller", is_admin=True)


@pytest.fixture()
def non_admin_session() -> Session:
    """Caller with ``USER_CAPS`` — denied on every P25 cap.

    ``USER_CAPS`` is no longer empty — CORE-C2R1 / ADR-0002 §am-3
    added the two skill-lifecycle capabilities — but it holds none
    of the capabilities under test here, so the denial paths are
    unaffected.
    """
    return Session.for_testing("alice-caller", is_admin=False)


@pytest.fixture()
def seeded_admin(tmp_server_db, fast_params):
    """One admin 'admin-caller' seeded — used by CLI integration tests."""
    _insert_first_admin(
        tmp_server_db, "admin-caller", "adminpw",
        params=fast_params, os_user="test-host",
    )
    return tmp_server_db


@pytest.fixture()
def seeded_user(seeded_admin, fast_params):
    """One regular user 'alice' seeded alongside the admin."""
    insert_user(
        seeded_admin, "alice", "alicepw",
        actor_role="user", params=fast_params,
    )
    seeded_admin.commit()
    return seeded_admin
