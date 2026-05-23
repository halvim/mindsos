"""
ADR-0040 / Phase 25 — :class:`Session` structurally satisfies
:class:`SessionProtocol`.

Enforces the KL ↔ Server alignment invariant at CI time. A rename or
shape drift on either side will fail this assertion.
"""

from __future__ import annotations

from mindsos_knowledge.types import SessionProtocol
from mindsos_server.session import Session


def test_session_for_testing_satisfies_session_protocol() -> None:
    """Real Session instances must isinstance-pass against the Protocol."""
    s = Session.for_testing("alice", is_admin=False)
    assert isinstance(s, SessionProtocol)


def test_admin_session_satisfies_session_protocol() -> None:
    """Admin variant also passes — capabilities set differs only in size."""
    s = Session.for_testing("admin", is_admin=True)
    assert isinstance(s, SessionProtocol)


def test_session_protocol_attribute_shape() -> None:
    """Manual shape check — fields named per ADR-0040 §Decision verbatim."""
    s = Session.for_testing("alice", is_admin=False)
    assert isinstance(s.session_id, str)
    assert isinstance(s.user_id, str)
    assert s.actor_role in ("user", "admin")
    # frozenset[str] structurally satisfies Iterable[str].
    assert all(isinstance(cap, str) for cap in s.capabilities)
    assert s.has("CAN_READ_OTHER_LOCALS") in (True, False)
