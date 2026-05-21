"""
Phase 19 session_from_token() tests per PB-8 (lazy expiry) + PB-14
(InvalidSessionError cause enum) + ADR-0003 §am1.

Verifies:
* Happy-path lookup returns Session.
* Sliding refresh: last_seen_at advances on each successful lookup.
* Capabilities resolved from current user role (not cached on session
  row) — admin user → ADMIN_CAPS, regular user → USER_CAPS (empty).
* Expired-sliding: row deleted + InvalidSessionError raised with
  EXPIRED_SLIDING cause.
* Expired-absolute: row deleted + InvalidSessionError raised with
  EXPIRED_ABSOLUTE cause (takes precedence over sliding).
* Not-found: InvalidSessionError raised with NOT_FOUND cause.
"""

from __future__ import annotations

import time

import pytest

from mindsos_server.capabilities import ADMIN_CAPS, USER_CAPS
from mindsos_server.errors import InvalidSessionCause, InvalidSessionError
from mindsos_server.sessions import (
    SessionTTL,
    _TEST_FAST_TTL,
    login,
    session_from_token,
)


class TestHappyPath:
    def test_lookup_returns_session(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        session = session_from_token(seeded_admin, result.token, ttl=fast_ttl)
        assert session.user_id == "admin"
        assert session.actor_role == "admin"
        assert session.session_id == result.session.session_id

    def test_admin_capabilities(self, seeded_admin, fast_params, fast_ttl) -> None:
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        session = session_from_token(seeded_admin, result.token, ttl=fast_ttl)
        assert session.capabilities == ADMIN_CAPS

    def test_user_capabilities_empty(
        self, seeded_user, fast_params, fast_ttl
    ) -> None:
        """USER_CAPS strictly empty in v1 per Phase 18 PB-12 / ADR-0002 §am1."""
        result = login(
            seeded_user, "alice", "alicepw", ttl=fast_ttl, params=fast_params
        )
        session = session_from_token(seeded_user, result.token, ttl=fast_ttl)
        assert session.capabilities == USER_CAPS
        assert session.capabilities == frozenset()


class TestSlidingRefresh:
    def test_last_seen_at_advances(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        original_last_seen = seeded_admin.execute(
            "SELECT last_seen_at FROM sessions WHERE session_id = ?",
            (result.session.session_id,),
        ).fetchone()[0]

        # Force >1ms gap so the ISO ms timestamp is different.
        time.sleep(0.005)

        session_from_token(seeded_admin, result.token, ttl=fast_ttl)

        new_last_seen = seeded_admin.execute(
            "SELECT last_seen_at FROM sessions WHERE session_id = ?",
            (result.session.session_id,),
        ).fetchone()[0]
        assert new_last_seen > original_last_seen


class TestExpiredSliding:
    def test_expired_sliding_raises(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        # Wait past sliding (1s) but NOT absolute (2s).
        time.sleep(1.2)
        with pytest.raises(InvalidSessionError) as exc_info:
            session_from_token(seeded_admin, result.token, ttl=fast_ttl)
        assert exc_info.value.cause == InvalidSessionCause.EXPIRED_SLIDING

    def test_expired_sliding_deletes_row(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        time.sleep(1.2)
        with pytest.raises(InvalidSessionError):
            session_from_token(seeded_admin, result.token, ttl=fast_ttl)
        rows = seeded_admin.execute(
            "SELECT session_id FROM sessions WHERE session_id = ?",
            (result.session.session_id,),
        ).fetchall()
        assert rows == []

    def test_expired_then_lookup_again_is_not_found(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        """After lazy delete on first expired lookup, the second
        lookup with the same token raises NOT_FOUND (the row is gone)."""
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        time.sleep(1.2)
        with pytest.raises(InvalidSessionError):
            session_from_token(seeded_admin, result.token, ttl=fast_ttl)
        with pytest.raises(InvalidSessionError) as exc_info:
            session_from_token(seeded_admin, result.token, ttl=fast_ttl)
        assert exc_info.value.cause == InvalidSessionCause.NOT_FOUND


class TestExpiredAbsolute:
    def test_expired_absolute_raises(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        # Refresh repeatedly to keep sliding alive while absolute ticks down.
        # _TEST_FAST_TTL: sliding=1s, absolute=2s. Refresh every 0.5s.
        time.sleep(0.5)
        session_from_token(seeded_admin, result.token, ttl=fast_ttl)
        time.sleep(0.5)
        session_from_token(seeded_admin, result.token, ttl=fast_ttl)
        time.sleep(0.5)
        session_from_token(seeded_admin, result.token, ttl=fast_ttl)
        # Now past absolute (2s); next lookup must raise EXPIRED_ABSOLUTE.
        time.sleep(0.7)
        with pytest.raises(InvalidSessionError) as exc_info:
            session_from_token(seeded_admin, result.token, ttl=fast_ttl)
        assert exc_info.value.cause == InvalidSessionCause.EXPIRED_ABSOLUTE


class TestNotFound:
    def test_random_token_not_found(self, tmp_server_db, fast_ttl) -> None:
        with pytest.raises(InvalidSessionError) as exc_info:
            session_from_token(
                tmp_server_db, "this-token-never-existed", ttl=fast_ttl
            )
        assert exc_info.value.cause == InvalidSessionCause.NOT_FOUND

    def test_logged_out_token_not_found(
        self, seeded_admin, fast_params, fast_ttl
    ) -> None:
        from mindsos_server.sessions import logout

        result = login(
            seeded_admin, "admin", "adminpw", ttl=fast_ttl, params=fast_params
        )
        logout(seeded_admin, result.token)
        with pytest.raises(InvalidSessionError) as exc_info:
            session_from_token(seeded_admin, result.token, ttl=fast_ttl)
        assert exc_info.value.cause == InvalidSessionCause.NOT_FOUND


class TestPublicMessageUniform:
    """PB-14 / ADR-0003 §am1: opaque public message across all three causes."""

    def test_uniform_public_message(self, tmp_server_db, fast_ttl) -> None:
        with pytest.raises(InvalidSessionError) as exc_info:
            session_from_token(tmp_server_db, "garbage", ttl=fast_ttl)
        assert str(exc_info.value) == "invalid session"
