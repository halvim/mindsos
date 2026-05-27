"""Phase 33 — fixtures for L3 write-capacity stub-path tests.

Extends Phase 30's session fixture with a configurable-capability
variant so cap-denial paths can be exercised. Phase 30's stock
``_LocalTestSession.has()`` returns ``True`` unconditionally; trace
cap-denial tests need a session where ``has(CAN_WRITE_GLOBAL)``
returns ``False`` (R3 §am-impl-4 + R3 PB-X).
"""

from __future__ import annotations

from typing import FrozenSet, Optional


class _CapAwareTestSession:
    """SessionProtocol-conforming session with a configurable capability set.

    ``caps=None`` → ``has()`` returns ``True`` for any capability
    (Phase 30 default behavior).
    ``caps=frozenset({...})`` → ``has(cap)`` returns ``cap in caps``.
    """

    def __init__(
        self,
        user_id: str = "alice",
        caps: Optional[FrozenSet[str]] = None,
    ) -> None:
        self.user_id = user_id
        self.session_id = f"test-session-{user_id}"
        self._caps: Optional[FrozenSet[str]] = caps

    def has(self, capability: str) -> bool:  # noqa: D401 — protocol stub
        if self._caps is None:
            return True
        return capability in self._caps


def build_session_with_caps(user_id: str, caps: FrozenSet[str]):
    """Build a test session that explicitly grants only ``caps``."""
    return _CapAwareTestSession(user_id=user_id, caps=caps)


def build_session_without_cap(user_id: str, capability: str):
    """Build a test session that holds every capability EXCEPT ``capability``.

    Implemented as the empty-cap-set variant — ``has(capability)``
    returns ``False`` for the named one; ``has(anything_else)`` also
    returns ``False``. Tests assert only the named denial; if a
    capacity body checks additional caps, extend the fixture.
    """
    return _CapAwareTestSession(user_id=user_id, caps=frozenset())


__all__ = [
    "build_session_with_caps",
    "build_session_without_cap",
]
