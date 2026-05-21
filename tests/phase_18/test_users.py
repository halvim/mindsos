"""
Tests for ``mindsos_server.users`` — Phase 18 PB-7 + PB-13 + PB-15 +
PB-22 + PB-23 + PB-24 + PB-29 + PB-30.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from mindsos_server._argon2 import Argon2Params
from mindsos_server.errors import (
    AuthFailedError,
    AuthFailureCause,
    UserAlreadyExistsError,
)
from mindsos_server.users import (
    User,
    _insert_first_admin,
    count_admins,
    insert_user,
    list_users,
    verify,
)


class TestUserDataclassShape:
    """PB-24 — User has no password_hash field; frozen + 4 fields."""

    def test_no_password_hash_field(self) -> None:
        assert "password_hash" not in User.__dataclass_fields__

    def test_fields_match_pb24(self) -> None:
        assert set(User.__dataclass_fields__.keys()) == {
            "user_id", "actor_role", "disabled", "created_at",
        }

    def test_user_is_frozen(self) -> None:
        u = User(
            user_id="alice",
            actor_role="user",
            disabled=False,
            created_at=datetime(2026, 5, 21),
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            u.user_id = "bob"  # type: ignore[misc]


class TestInsertUser:
    """insert_user roundtrip + UNIQUE handling + charset validation."""

    def test_insert_returns_user(self, tmp_server_db, fast_params: Argon2Params) -> None:
        user = insert_user(tmp_server_db, "alice", "hunter2", params=fast_params)
        assert user.user_id == "alice"
        assert user.actor_role == "user"
        assert user.disabled is False

    def test_insert_admin_role(self, tmp_server_db, fast_params: Argon2Params) -> None:
        user = insert_user(
            tmp_server_db, "alice", "hunter2", actor_role="admin", params=fast_params
        )
        assert user.actor_role == "admin"

    def test_duplicate_raises_user_already_exists(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        insert_user(tmp_server_db, "alice", "hunter2", params=fast_params)
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            insert_user(tmp_server_db, "alice", "different-pw", params=fast_params)
        assert exc_info.value.user_id == "alice"

    def test_invalid_user_id_charset(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        """PB-7 — _USER_ID_RE inherited from KL; ':' must reject."""
        with pytest.raises(ValueError):
            insert_user(tmp_server_db, "alice:bob", "hunter2", params=fast_params)

    def test_audit_row_written(self, tmp_server_db, fast_params: Argon2Params) -> None:
        """ADR-0013 — insert_user writes EVT_ADMIN_CREATE_USER row."""
        insert_user(
            tmp_server_db, "alice", "hunter2", params=fast_params,
            audit_actor="bob",
        )
        rows = tmp_server_db.execute(
            "SELECT actor_user, event, target_user FROM audit WHERE event=?",
            ("EVT_ADMIN_CREATE_USER",),
        ).fetchall()
        assert len(rows) == 1
        assert rows[0] == ("bob", "EVT_ADMIN_CREATE_USER", "alice")


class TestListUsers:
    """list_users returns sorted User list; no password_hash leak."""

    def test_empty_list(self, tmp_server_db) -> None:
        assert list_users(tmp_server_db) == []

    def test_sorted_by_user_id(self, tmp_server_db, fast_params: Argon2Params) -> None:
        insert_user(tmp_server_db, "charlie", "pw", params=fast_params)
        insert_user(tmp_server_db, "alice", "pw", params=fast_params)
        insert_user(tmp_server_db, "bob", "pw", params=fast_params)
        users = list_users(tmp_server_db)
        assert [u.user_id for u in users] == ["alice", "bob", "charlie"]

    def test_no_password_hash_leak(self, tmp_server_db, fast_params: Argon2Params) -> None:
        insert_user(tmp_server_db, "alice", "secret-pw", params=fast_params)
        users = list_users(tmp_server_db)
        # User dataclass has no password_hash field; verified at class level.
        # Also verify the dataclass repr does not include the string "secret-pw".
        for u in users:
            assert "secret-pw" not in repr(u)
            assert "password" not in repr(u).lower()


class TestVerifyRoundtrip:
    """verify success returns User per PB-13."""

    def test_correct_password_returns_user(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        insert_user(tmp_server_db, "alice", "hunter2", params=fast_params)
        user = verify(tmp_server_db, "alice", "hunter2", params=fast_params)
        assert user.user_id == "alice"


class TestVerifyAuthFailureCauses:
    """PB-23 — single AuthFailedError; private cause for 3 failure modes."""

    def test_unknown_user_cause(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        with pytest.raises(AuthFailedError) as exc_info:
            verify(tmp_server_db, "nobody", "any-pw", params=fast_params)
        assert exc_info.value.cause == AuthFailureCause.UNKNOWN_USER
        # PB-23: public message uniform.
        assert str(exc_info.value) == "auth failed"

    def test_bad_password_cause(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        insert_user(tmp_server_db, "alice", "correct", params=fast_params)
        with pytest.raises(AuthFailedError) as exc_info:
            verify(tmp_server_db, "alice", "wrong", params=fast_params)
        assert exc_info.value.cause == AuthFailureCause.BAD_PASSWORD
        assert str(exc_info.value) == "auth failed"

    def test_disabled_cause(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        """PB-15 — verify honors disabled column."""
        insert_user(tmp_server_db, "alice", "correct", params=fast_params)
        tmp_server_db.execute(
            "UPDATE users SET disabled = 1 WHERE user_id = ?", ("alice",)
        )
        tmp_server_db.commit()
        with pytest.raises(AuthFailedError) as exc_info:
            verify(tmp_server_db, "alice", "correct", params=fast_params)
        assert exc_info.value.cause == AuthFailureCause.DISABLED
        assert str(exc_info.value) == "auth failed"

    def test_audit_row_written_on_failure(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        """EVT_LOGIN_FAILED audit row per ADR-0013."""
        with pytest.raises(AuthFailedError):
            verify(tmp_server_db, "nobody", "any", params=fast_params)
        rows = tmp_server_db.execute(
            "SELECT event, actor_user, target_user, extra_json FROM audit "
            "WHERE event=?",
            ("EVT_LOGIN_FAILED",),
        ).fetchall()
        assert len(rows) == 1
        # Private cause leaks into audit per PB-23 design (server-internal only).
        assert "UNKNOWN_USER" in rows[0][3]


class TestInsertFirstAdmin:
    """PB-9 + PB-29 — pure insert; OS-user audit; admin role hardcoded."""

    def test_creates_admin(self, tmp_server_db, fast_params: Argon2Params) -> None:
        user = _insert_first_admin(
            tmp_server_db, "admin", "rootpw",
            params=fast_params, os_user="hostuser",
        )
        assert user.user_id == "admin"
        assert user.actor_role == "admin"

    def test_audit_uses_os_user_as_actor(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        _insert_first_admin(
            tmp_server_db, "admin", "rootpw",
            params=fast_params, os_user="hostuser",
        )
        rows = tmp_server_db.execute(
            "SELECT actor_user, event, target_user FROM audit WHERE event=?",
            ("EVT_BOOTSTRAP",),
        ).fetchall()
        assert len(rows) == 1
        assert rows[0] == ("hostuser", "EVT_BOOTSTRAP", "admin")

    def test_duplicate_raises_user_already_exists(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        _insert_first_admin(
            tmp_server_db, "admin", "rootpw",
            params=fast_params, os_user="hostuser",
        )
        with pytest.raises(UserAlreadyExistsError):
            _insert_first_admin(
                tmp_server_db, "admin", "anything",
                params=fast_params, os_user="hostuser",
            )


class TestCountAdmins:
    """PB-29 — count_admins used by CLI idempotency check."""

    def test_zero_on_fresh_db(self, tmp_server_db) -> None:
        assert count_admins(tmp_server_db) == 0

    def test_counts_active_admins(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        insert_user(
            tmp_server_db, "alice", "pw", actor_role="admin", params=fast_params
        )
        insert_user(tmp_server_db, "bob", "pw", params=fast_params)
        insert_user(
            tmp_server_db, "carol", "pw", actor_role="admin", params=fast_params
        )
        assert count_admins(tmp_server_db) == 2

    def test_disabled_admin_excluded(
        self, tmp_server_db, fast_params: Argon2Params
    ) -> None:
        insert_user(
            tmp_server_db, "alice", "pw", actor_role="admin", params=fast_params
        )
        tmp_server_db.execute(
            "UPDATE users SET disabled = 1 WHERE user_id = ?", ("alice",)
        )
        tmp_server_db.commit()
        assert count_admins(tmp_server_db) == 0
