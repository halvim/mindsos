"""Phase 28 — SessionProtocol parity (ADR-0040 §amendment-2)."""

from __future__ import annotations

from mindsos_capacity import CAN_WRITE_GLOBAL, SessionProtocol as L3_SessionProtocol
from mindsos_knowledge.types import SessionProtocol as L2_SessionProtocol
from mindsos_server.session import Session


def test_session_protocol_parity_with_l2_and_real_session():
    l3_attrs = set(L3_SessionProtocol.__annotations__.keys())
    l2_attrs = set(L2_SessionProtocol.__annotations__.keys())
    assert l3_attrs == l2_attrs, (
        f"SessionProtocol attribute drift between L3 and L2: "
        f"L3={l3_attrs!r}, L2={l2_attrs!r}. Update either layer."
    )
    assert hasattr(L3_SessionProtocol, "has")
    assert hasattr(L2_SessionProtocol, "has")
    sess_user = Session.for_testing("alice", is_admin=False)
    assert isinstance(sess_user, L3_SessionProtocol)
    sess_admin = Session.for_testing("root", is_admin=True)
    assert isinstance(sess_admin, L3_SessionProtocol)
    assert sess_admin.has(CAN_WRITE_GLOBAL)
    assert not sess_user.has(CAN_WRITE_GLOBAL)
