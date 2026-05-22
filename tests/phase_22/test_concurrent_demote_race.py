"""
Phase 22 R4 PB-24 — concurrent admin verb race regression test.

Two threaded connections each demote one of two admins. Without
``BEGIN IMMEDIATE`` (R4 PB-24 admin_tx wrapper) both verbs' snapshots
could see the OTHER admin as still active; both would pass
``_assert_not_sole_admin`` and both would commit, leaving 0 active
admins.

With ``admin_tx`` wrapping, the second BEGIN IMMEDIATE blocks (up to
``busy_timeout=5000`` ms set in :func:`mindsos_server._db.open_db`)
until the first commits; the second verb's snapshot then reflects the
first commit; ``_assert_not_sole_admin`` correctly fires LastAdminError.

Test asserts EXACTLY ONE of the two demotes succeeds; the other raises
LastAdminError. The "0 active admins" failure mode does NOT occur.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from mindsos_server._argon2 import _TEST_FAST_PARAMS
from mindsos_server._db import open_db
from mindsos_server._schema import init_or_migrate
from mindsos_server.admin import admin_demote_user
from mindsos_server.errors import LastAdminError
from mindsos_server.session import Session
from mindsos_server.users import _insert_first_admin, count_admins, insert_user


@pytest.fixture()
def two_admin_db_path(tmp_path: Path) -> Path:
    """Persistent on-disk DB with two admins ('a1' + 'a2')."""
    db_path = tmp_path / "race.db"
    with open_db(db_path) as conn:
        init_or_migrate(conn)
        _insert_first_admin(
            conn, "a1", "pw1",
            params=_TEST_FAST_PARAMS, os_user="test-host",
        )
        insert_user(
            conn, "a2", "pw2",
            actor_role="admin", params=_TEST_FAST_PARAMS,
            audit_actor="test-host",
        )
    return db_path


class TestConcurrentDemoteRace:
    def test_exactly_one_succeeds(self, two_admin_db_path):
        admin_session = Session.for_testing("caller", is_admin=True)
        # Use a synchronization barrier so both threads attempt the
        # mutating SQL at the same moment.
        start = threading.Barrier(2)
        results: list[Exception | None] = [None, None]

        def _demote(idx: int, target: str) -> None:
            try:
                with open_db(two_admin_db_path) as conn:
                    start.wait(timeout=5.0)
                    admin_demote_user(
                        conn, admin_session, target_user_id=target
                    )
                results[idx] = None
            except Exception as e:
                results[idx] = e

        t1 = threading.Thread(target=_demote, args=(0, "a1"))
        t2 = threading.Thread(target=_demote, args=(1, "a2"))
        t1.start()
        t2.start()
        t1.join(timeout=15.0)
        t2.join(timeout=15.0)

        # Exactly one Result was None (success), one was LastAdminError.
        # (We do NOT assert which one — race is non-deterministic; we
        # assert the invariant the wrapper protects.)
        successes = sum(1 for r in results if r is None)
        last_admin_errors = sum(
            1 for r in results if isinstance(r, LastAdminError)
        )
        assert successes == 1, f"results={results!r}"
        assert last_admin_errors == 1, f"results={results!r}"

        # Final state: exactly ONE active admin remaining.
        with open_db(two_admin_db_path) as conn:
            count = count_admins(conn)
        assert count == 1, (
            f"sole-admin invariant violated; count_admins={count}"
        )
