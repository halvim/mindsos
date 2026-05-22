"""
Phase 22 R4 PB-24 — admin_tx context manager (BEGIN IMMEDIATE wrapper).

Verifies:
* Wrapper commits on clean exit.
* Wrapper rolls back on exception.
* `conn.in_transaction` true inside the block.
"""

from __future__ import annotations

import pytest

from mindsos_server.admin import admin_tx


class TestAdminTx:
    def test_commits_on_clean_exit(self, seeded_admin):
        with admin_tx(seeded_admin):
            seeded_admin.execute(
                "UPDATE users SET disabled = 1 WHERE user_id = 'admin'"
            )
        # After exit, change visible in a fresh read
        row = seeded_admin.execute(
            "SELECT disabled FROM users WHERE user_id = 'admin'"
        ).fetchone()
        assert int(row[0]) == 1

    def test_rollback_on_exception(self, seeded_admin):
        class _Boom(Exception):
            pass

        with pytest.raises(_Boom):
            with admin_tx(seeded_admin):
                seeded_admin.execute(
                    "UPDATE users SET disabled = 1 WHERE user_id = 'admin'"
                )
                raise _Boom()
        # Rollback: change NOT persisted
        row = seeded_admin.execute(
            "SELECT disabled FROM users WHERE user_id = 'admin'"
        ).fetchone()
        assert int(row[0]) == 0

    def test_in_transaction_inside_block(self, seeded_admin):
        assert not seeded_admin.in_transaction
        with admin_tx(seeded_admin):
            # BEGIN IMMEDIATE → conn.in_transaction True
            assert seeded_admin.in_transaction
        assert not seeded_admin.in_transaction
