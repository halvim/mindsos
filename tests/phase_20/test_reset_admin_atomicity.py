"""
Phase 20 reset_admin() transactional atomicity (PB-R).

Per Phase 20 PB-R: single SQLite transaction, DELETE-then-UPDATE
order. If any step in the body raises, the connection's implicit
transaction is NOT committed and SQLite rolls back automatically on
the next non-committed operation (or on close).

This file verifies the rollback semantic by injecting failures at the
two write sites:

* mid-`hash_password` failure (e.g., argon2 raises) — UPDATE never
  runs; DELETE was already issued but is rolled back by the lack of
  commit().
* mid-`write_audit` failure — DELETE + UPDATE both rolled back.

The injection uses ``monkeypatch`` against the module-level helpers
that ``reset_admin`` calls. This is white-box but unavoidable for
exercising the partial-failure path without a Real Crash.
"""

from __future__ import annotations

import pytest

from mindsos_server import admin as admin_module
from mindsos_server.admin import reset_admin


class TestAtomicityOnHashPasswordFailure:
    """If hash_password raises, DELETE must be rolled back (no commit)."""

    def test_sessions_survive_when_hash_password_raises(
        self,
        seeded_admin_with_sessions,
        fast_params,
        monkeypatch,
    ) -> None:
        conn, original_session_ids = seeded_admin_with_sessions

        def _boom(*_args, **_kwargs):
            raise RuntimeError("simulated argon2 failure")

        # Patch the symbol that admin.py imported (not the source module).
        monkeypatch.setattr(admin_module, "hash_password", _boom)

        with pytest.raises(RuntimeError, match="simulated argon2 failure"):
            reset_admin(
                conn,
                "admin",
                "newpw",
                os_user="test-host",
                params=fast_params,
            )

        # Rollback verification: sessions are still present after the
        # exception, because conn.commit() never ran.
        # NOTE: SQLite's default isolation means uncommitted writes are
        # visible to the same connection. To verify rollback, the
        # implicit transaction must be aborted. Issue a ROLLBACK then
        # re-query.
        conn.rollback()

        rows = conn.execute(
            "SELECT session_id FROM sessions WHERE user_id = 'admin'"
        ).fetchall()
        survived = sorted(r[0] for r in rows)
        assert survived == sorted(original_session_ids), (
            "PB-R atomicity: DELETE must roll back when subsequent "
            "step raises"
        )

    def test_password_hash_unchanged_when_hash_raises(
        self,
        seeded_admin,
        fast_params,
        monkeypatch,
    ) -> None:
        original = seeded_admin.execute(
            "SELECT password_hash FROM users WHERE user_id = 'admin'"
        ).fetchone()[0]

        def _boom(*_args, **_kwargs):
            raise RuntimeError("simulated argon2 failure")

        monkeypatch.setattr(admin_module, "hash_password", _boom)

        with pytest.raises(RuntimeError):
            reset_admin(
                seeded_admin,
                "admin",
                "newpw",
                os_user="test-host",
                params=fast_params,
            )

        seeded_admin.rollback()
        after = seeded_admin.execute(
            "SELECT password_hash FROM users WHERE user_id = 'admin'"
        ).fetchone()[0]
        assert original == after


class TestAtomicityOnWriteAuditFailure:
    """If a write_audit call raises, DELETE + UPDATE must be rolled back."""

    def test_state_rolled_back_when_audit_raises(
        self,
        seeded_admin_with_sessions,
        fast_params,
        monkeypatch,
    ) -> None:
        conn, original_session_ids = seeded_admin_with_sessions
        original_hash = conn.execute(
            "SELECT password_hash FROM users WHERE user_id = 'admin'"
        ).fetchone()[0]

        def _boom(*_args, **_kwargs):
            raise RuntimeError("simulated audit-write failure")

        monkeypatch.setattr(admin_module, "write_audit", _boom)

        with pytest.raises(RuntimeError, match="simulated audit-write failure"):
            reset_admin(
                conn,
                "admin",
                "newpw",
                os_user="test-host",
                params=fast_params,
            )

        # Roll back the implicit tx and re-query.
        conn.rollback()

        # Sessions intact.
        rows = conn.execute(
            "SELECT session_id FROM sessions WHERE user_id = 'admin'"
        ).fetchall()
        assert sorted(r[0] for r in rows) == sorted(original_session_ids)

        # password_hash intact.
        after_hash = conn.execute(
            "SELECT password_hash FROM users WHERE user_id = 'admin'"
        ).fetchone()[0]
        assert original_hash == after_hash


class TestHappyPathCommits:
    """Sanity: on success, the transaction DOES commit (no rollback needed)."""

    def test_changes_persist_after_close_and_reopen(
        self,
        tmp_server_db_path,
        fast_params,
    ) -> None:
        from mindsos_server._db import open_db
        from mindsos_server._schema import init_or_migrate
        from mindsos_server.users import _insert_first_admin

        # Bootstrap then reset in one connection.
        with open_db(tmp_server_db_path) as conn1:
            init_or_migrate(conn1)
            _insert_first_admin(
                conn1,
                "admin",
                "originalpw",
                params=fast_params,
                os_user="host",
            )
            original = conn1.execute(
                "SELECT password_hash FROM users WHERE user_id = 'admin'"
            ).fetchone()[0]
            reset_admin(
                conn1,
                "admin",
                "newpw",
                os_user="host",
                params=fast_params,
            )
            rotated = conn1.execute(
                "SELECT password_hash FROM users WHERE user_id = 'admin'"
            ).fetchone()[0]
            assert original != rotated

        # Re-open and confirm the rotation persisted (commit() ran).
        with open_db(tmp_server_db_path) as conn2:
            persisted = conn2.execute(
                "SELECT password_hash FROM users WHERE user_id = 'admin'"
            ).fetchone()[0]
            assert persisted == rotated
