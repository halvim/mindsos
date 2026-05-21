"""
Tests for ``mindsos_server.session`` — Phase 18 PB-33 + PB-6.
"""

from __future__ import annotations

import pytest

from mindsos_server.capabilities import (
    ADMIN_CAPS,
    CAN_MANAGE_USERS,
    USER_CAPS,
)
from mindsos_server.session import Session


class TestSessionShapeMatchesProtocol:
    """PB-33 — Session matches SessionProtocol exactly: 4 fields + has()."""

    def test_required_fields(self) -> None:
        fields = set(Session.__dataclass_fields__.keys())
        assert fields == {"session_id", "user_id", "actor_role", "capabilities"}

    def test_session_is_frozen(self) -> None:
        s = Session(
            session_id="sid",
            user_id="alice",
            actor_role="user",
            capabilities=frozenset(),
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            s.user_id = "bob"  # type: ignore[misc]

    def test_capabilities_is_frozenset(self) -> None:
        s = Session(
            session_id="sid",
            user_id="alice",
            actor_role="admin",
            capabilities=ADMIN_CAPS,
        )
        assert isinstance(s.capabilities, frozenset)

    def test_has_returns_true_when_present(self) -> None:
        s = Session(
            session_id="sid",
            user_id="alice",
            actor_role="admin",
            capabilities=ADMIN_CAPS,
        )
        assert s.has(CAN_MANAGE_USERS) is True

    def test_has_returns_false_when_absent(self) -> None:
        s = Session(
            session_id="sid",
            user_id="alice",
            actor_role="user",
            capabilities=USER_CAPS,
        )
        assert s.has(CAN_MANAGE_USERS) is False


class TestSessionForTesting:
    """ADR-0013 + Phase 18 PB-6 — for_testing shim."""

    def test_user_session_has_user_caps(self) -> None:
        s = Session.for_testing("alice", is_admin=False)
        assert s.capabilities == USER_CAPS
        assert s.actor_role == "user"

    def test_admin_session_has_admin_caps(self) -> None:
        s = Session.for_testing("alice", is_admin=True)
        assert s.capabilities == ADMIN_CAPS
        assert s.actor_role == "admin"

    def test_default_synthetic_session_id(self) -> None:
        """ADR-0013 — 'stable synthetic session_id'."""
        s = Session.for_testing("alice")
        assert s.session_id == "test-alice"

    def test_custom_session_id(self) -> None:
        s = Session.for_testing("alice", session_id="custom-sid")
        assert s.session_id == "custom-sid"

    def test_capabilities_override(self) -> None:
        s = Session.for_testing("alice", capabilities=[CAN_MANAGE_USERS])
        assert s.capabilities == frozenset({CAN_MANAGE_USERS})
        # actor_role still defaults to user (override is independent).
        assert s.actor_role == "user"

    def test_for_testing_returns_immutable_session(self) -> None:
        s = Session.for_testing("alice", is_admin=True)
        with pytest.raises(Exception):
            s.user_id = "bob"  # type: ignore[misc]
