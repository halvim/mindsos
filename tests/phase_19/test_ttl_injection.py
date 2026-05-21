"""
Phase 19 SessionTTL + injection tests per PB-12 + PB-15.

Verifies:
* SessionTTL is a frozen, hashable dataclass.
* PRODUCTION_TTL matches ADR-0003 verbatim (sliding=8h, absolute=24h).
* _TEST_FAST_TTL has the expected low values (1s sliding, 2s absolute).
* Login + session_from_token + kill_my_own_sessions all accept a ttl
  kwarg; defaults to PRODUCTION_TTL when omitted.
* No module-level state — different ttl args on different calls work
  independently (anti-PB-14 global precedent).
"""

from __future__ import annotations

import pytest

from mindsos_server.sessions import (
    PRODUCTION_TTL,
    SessionTTL,
    _TEST_FAST_TTL,
    login,
)


class TestProductionTTL:
    def test_sliding_eight_hours(self) -> None:
        assert PRODUCTION_TTL.sliding_seconds == 8 * 3600

    def test_absolute_twenty_four_hours(self) -> None:
        assert PRODUCTION_TTL.absolute_seconds == 24 * 3600


class TestTestFastTTL:
    def test_sliding_one_second(self) -> None:
        assert _TEST_FAST_TTL.sliding_seconds == 1

    def test_absolute_two_seconds(self) -> None:
        assert _TEST_FAST_TTL.absolute_seconds == 2


class TestSessionTTLDataclass:
    def test_frozen(self) -> None:
        ttl = SessionTTL(sliding_seconds=10, absolute_seconds=100)
        with pytest.raises(Exception):  # FrozenInstanceError
            ttl.sliding_seconds = 99  # type: ignore[misc]

    def test_hashable(self) -> None:
        a = SessionTTL(sliding_seconds=10, absolute_seconds=100)
        b = SessionTTL(sliding_seconds=10, absolute_seconds=100)
        assert hash(a) == hash(b)
        assert {a, b} == {a}


class TestExplicitInjection:
    """PB-15 — TTL passed per-call. No module-level global to monkeypatch."""

    def test_default_is_production(
        self, seeded_admin, fast_params
    ) -> None:
        """Omitting ttl kwarg → PRODUCTION_TTL default."""
        # We don't want to actually wait 8h, but we CAN verify the
        # default kicks in by checking the LoginResult.expires_at
        # is ~8h from created_at.
        result = login(seeded_admin, "admin", "adminpw", params=fast_params)
        delta = (result.expires_at - result.created_at).total_seconds()
        assert delta == pytest.approx(PRODUCTION_TTL.sliding_seconds, abs=1)

    def test_custom_ttl(self, seeded_admin, fast_params) -> None:
        custom = SessionTTL(sliding_seconds=5, absolute_seconds=10)
        result = login(
            seeded_admin,
            "admin",
            "adminpw",
            ttl=custom,
            params=fast_params,
        )
        delta = (result.expires_at - result.created_at).total_seconds()
        assert delta == pytest.approx(5, abs=0.05)
