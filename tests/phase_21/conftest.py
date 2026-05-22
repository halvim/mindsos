"""
Shared fixtures for Phase 21 tests
(``mindsos_server.admin.admin_query_audit`` + ``mindsos_server.authz._require_or_audit``).

Mirrors :mod:`tests.phase_20.conftest` shape — fixtures are scoped to
this phase's directory; pytest does not auto-inherit from sibling
phase conftests, so we duplicate the seed fixtures here and add the
Phase 21-specific ones.

Phase 21 fixtures added on top of Phase 19/20's:

* :func:`admin_session` — :meth:`Session.for_testing` with
  ``is_admin=True`` (``ADMIN_CAPS``, includes ``CAN_VIEW_AUDIT_LOG``).
* :func:`user_session` — :meth:`Session.for_testing` with
  ``is_admin=False`` (``USER_CAPS`` = empty per ADR-0002 §am1).
* :func:`auditor_only_session` — minimal session holding ONLY
  ``CAN_VIEW_AUDIT_LOG`` (verifies the capability-based design from
  ADR-0002 — read access without other admin powers).
* :func:`seeded_audit_rows` — populate the ``audit`` table with N
  diverse rows (multi-actor / multi-event / multi-target / time-spanning)
  so reader filter tests have stable fixtures to query against.

Phase 21 does NOT use ``_TEST_FAST_PARAMS`` / ``_TEST_FAST_TTL`` —
the reader doesn't touch argon2 or session minting. The wrapper
``_require_or_audit`` uses :meth:`Session.for_testing` per ADR-0013
§Consequences.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterator

import pytest

from mindsos_server._db import open_db
from mindsos_server._schema import init_or_migrate
from mindsos_server.audit import (
    EVT_BOOTSTRAP,
    EVT_KILL_SESSION,
    EVT_LOGIN,
    EVT_LOGIN_FAILED,
    EVT_LOGOUT,
    EVT_PERMISSION_DENIED,
    EVT_RESET_ADMIN,
    write_audit,
)
from mindsos_server.capabilities import CAN_VIEW_AUDIT_LOG
from mindsos_server.session import Session


# ---------------------------------------------------------------------------
# DB / schema fixtures (mirrors Phase 20 shape)
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_server_db_path(tmp_path: Path) -> Path:
    """Path to a tmp ``server.db`` (file doesn't exist yet)."""
    return tmp_path / "server.db"


@pytest.fixture()
def tmp_server_db(tmp_server_db_path: Path) -> Iterator:
    """
    Open a fresh ``server.db`` at a tmp path, migrate to v3 (Phase 21
    schema includes ``idx_audit_target`` per PB-7), yield the
    connection.
    """
    with open_db(tmp_server_db_path) as conn:
        init_or_migrate(conn)
        yield conn


# ---------------------------------------------------------------------------
# Session fixtures (PB-6 + PB-13 + ADR-0013 §Consequences)
# ---------------------------------------------------------------------------


@pytest.fixture()
def admin_session() -> Session:
    """
    Admin session via :meth:`Session.for_testing` — gets ``ADMIN_CAPS``
    bundle which includes ``CAN_VIEW_AUDIT_LOG`` per ADR-0002.
    """
    return Session.for_testing("admin", is_admin=True)


@pytest.fixture()
def user_session() -> Session:
    """
    Non-admin session — capabilities default to ``USER_CAPS`` which
    is strictly empty per ADR-0002 §am1. Should be denied by
    ``_require_or_audit(CAN_VIEW_AUDIT_LOG)``.
    """
    return Session.for_testing("alice", is_admin=False)


@pytest.fixture()
def auditor_only_session() -> Session:
    """
    Minimal capability bundle: ONLY ``CAN_VIEW_AUDIT_LOG``. Verifies
    that the capability-based design from ADR-0002 grants read access
    without other admin powers — a future "auditor role" pattern.
    """
    return Session.for_testing(
        "auditor", is_admin=False, capabilities={CAN_VIEW_AUDIT_LOG}
    )


# ---------------------------------------------------------------------------
# Seeded audit-row fixtures (PHASE_21_DESIGN_LOG §5 reader-only tests)
# ---------------------------------------------------------------------------


@pytest.fixture()
def insert_audit_row(tmp_server_db) -> Callable[..., int]:
    """
    Insert a single audit row directly via SQL with a caller-supplied
    ``ts``. Returns the row's ``id``.

    Phase 21 tests need TIME-CONTROLLED audit rows so they can assert
    inclusive/exclusive bounds at known timestamps. The default
    ``write_audit`` helper uses :func:`_now_utc_iso` which is not
    test-controllable. This fixture inserts directly to bypass that.
    """

    def _insert(
        ts: str,
        *,
        actor: str | None,
        event: str,
        target: str | None = None,
        extra: dict | None = None,
    ) -> int:
        cursor = tmp_server_db.execute(
            "INSERT INTO audit "
            "(ts, actor_user, event, target_user, extra_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                ts,
                actor,
                event,
                target,
                json.dumps(extra) if extra is not None else "{}",
            ),
        )
        tmp_server_db.commit()
        return int(cursor.lastrowid)

    return _insert


@pytest.fixture()
def seeded_audit_rows(insert_audit_row):
    """
    Populate the audit table with 8 diverse rows spanning multiple
    actors / events / targets / timestamps. Returns the list of
    inserted row ids in insertion order.

    Layout (id-order; ts-order matches id-order since ts is monotonic
    in insertion order):

    | id | ts (Z)                  | actor   | event                   | target |
    |----|-------------------------|---------|-------------------------|--------|
    | 1  | 2026-05-21T00:00:00.000 | host    | EVT_BOOTSTRAP           | admin  |
    | 2  | 2026-05-21T01:00:00.000 | admin   | EVT_LOGIN               | NULL   |
    | 3  | 2026-05-21T02:00:00.000 | alice   | EVT_LOGIN_FAILED        | NULL   |
    | 4  | 2026-05-21T03:00:00.000 | admin   | EVT_LOGOUT              | NULL   |
    | 5  | 2026-05-21T04:00:00.000 | host    | EVT_RESET_ADMIN         | admin  |
    | 6  | 2026-05-21T05:00:00.000 | host    | EVT_KILL_SESSION        | admin  |
    | 7  | 2026-05-21T06:00:00.000 | alice   | EVT_LOGIN               | NULL   |
    | 8  | 2026-05-21T07:00:00.000 | alice   | EVT_LOGOUT              | NULL   |

    Tests can filter by any combination and predict the expected
    id-list precisely.
    """
    rows = [
        ("2026-05-21T00:00:00.000Z", "host",  EVT_BOOTSTRAP,    "admin"),
        ("2026-05-21T01:00:00.000Z", "admin", EVT_LOGIN,        None),
        ("2026-05-21T02:00:00.000Z", "alice", EVT_LOGIN_FAILED, None),
        ("2026-05-21T03:00:00.000Z", "admin", EVT_LOGOUT,       None),
        ("2026-05-21T04:00:00.000Z", "host",  EVT_RESET_ADMIN,  "admin"),
        ("2026-05-21T05:00:00.000Z", "host",  EVT_KILL_SESSION, "admin"),
        ("2026-05-21T06:00:00.000Z", "alice", EVT_LOGIN,        None),
        ("2026-05-21T07:00:00.000Z", "alice", EVT_LOGOUT,       None),
    ]
    ids: list[int] = []
    for ts, actor, event, target in rows:
        rid = insert_audit_row(ts, actor=actor, event=event, target=target)
        ids.append(rid)
    return ids
