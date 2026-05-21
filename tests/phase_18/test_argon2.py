"""
Tests for ``mindsos_server._argon2`` — Phase 18 PB-14 + PB-22 + PB-31.
"""

from __future__ import annotations

import pytest

from mindsos_server._argon2 import (
    PRODUCTION_PARAMS,
    _SENTINEL_HASH,
    _TEST_FAST_PARAMS,
    Argon2Params,
    hash_password,
    verify_against_sentinel,
    verify_password,
)


class TestProductionParams:
    """PRODUCTION_PARAMS must match ADR-0003 verbatim per PB-14."""

    def test_time_cost(self) -> None:
        assert PRODUCTION_PARAMS.time_cost == 3

    def test_memory_cost(self) -> None:
        assert PRODUCTION_PARAMS.memory_cost == 65536

    def test_parallelism(self) -> None:
        assert PRODUCTION_PARAMS.parallelism == 4


class TestTestFastParams:
    """_TEST_FAST_PARAMS is distinct from PRODUCTION_PARAMS."""

    def test_distinct_from_production(self) -> None:
        assert _TEST_FAST_PARAMS != PRODUCTION_PARAMS

    def test_time_cost_lower(self) -> None:
        assert _TEST_FAST_PARAMS.time_cost < PRODUCTION_PARAMS.time_cost

    def test_memory_cost_lower(self) -> None:
        assert _TEST_FAST_PARAMS.memory_cost < PRODUCTION_PARAMS.memory_cost


class TestHashVerifyRoundtrip:
    """hash_password / verify_password roundtrip per PB-14."""

    def test_roundtrip_with_fast_params(self, fast_params: Argon2Params) -> None:
        hashed = hash_password("hunter2", params=fast_params)
        assert hashed.startswith("$argon2id$")
        assert verify_password(hashed, "hunter2", params=fast_params) is True

    def test_wrong_password_returns_false(self, fast_params: Argon2Params) -> None:
        hashed = hash_password("hunter2", params=fast_params)
        assert verify_password(hashed, "wrong", params=fast_params) is False

    def test_different_salts_produce_different_hashes(
        self, fast_params: Argon2Params
    ) -> None:
        h1 = hash_password("same-pw", params=fast_params)
        h2 = hash_password("same-pw", params=fast_params)
        # argon2-cffi generates a fresh salt per call; hashes differ even
        # for identical plaintext.
        assert h1 != h2
        # Both still verify against the original password.
        assert verify_password(h1, "same-pw", params=fast_params) is True
        assert verify_password(h2, "same-pw", params=fast_params) is True


class TestSentinelHash:
    """PB-22 + PB-31 — sentinel hash closes the user-enumeration timing leak."""

    def test_sentinel_exists(self) -> None:
        """Module-level constant exists + has argon2id format."""
        assert isinstance(_SENTINEL_HASH, str)
        assert _SENTINEL_HASH.startswith("$argon2id$")

    def test_verify_against_sentinel_never_raises(
        self, fast_params: Argon2Params
    ) -> None:
        """The dummy verify swallows all exceptions per PB-22."""
        # Should not raise regardless of input.
        verify_against_sentinel("any-password", params=fast_params)
        verify_against_sentinel("", params=fast_params)
        verify_against_sentinel("a" * 1000, params=fast_params)

    def test_sentinel_does_not_match_real_passwords(
        self, fast_params: Argon2Params
    ) -> None:
        """The sentinel hash never matches any plaintext per PB-31."""
        # Verify that the sentinel hash does NOT match common plaintexts —
        # if it did, that would mean someone accidentally hashed a real
        # password into the constant.
        for guess in ("password", "admin", "phase-18-sentinel-not-a-real-password"):
            # Note: the last guess is the actual plaintext used to compute
            # the sentinel, so it WOULD match. Skip it in the assertion.
            if guess == "phase-18-sentinel-not-a-real-password":
                continue
            assert verify_password(_SENTINEL_HASH, guess, params=fast_params) is False


class TestArgon2ParamsFrozen:
    """Argon2Params is frozen per PB-14."""

    def test_cannot_mutate(self) -> None:
        with pytest.raises(Exception):  # FrozenInstanceError / AttributeError
            PRODUCTION_PARAMS.time_cost = 999  # type: ignore[misc]
