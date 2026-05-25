"""Phase 28 — CAN_WRITE_GLOBAL gate (ADR-0078 + ADR-0080)."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CAN_WRITE_GLOBAL,
    CapacityLayer,
    CATEGORY_PERCEPTION,
)
from mindsos_server.session import Session


def _layer():
    return CapacityLayer(categories=(CATEGORY_PERCEPTION,))


def test_gate_refuses_user_session_without_capability():
    cl = _layer()
    user_sess = Session.for_testing("alice", is_admin=False)
    assert not user_sess.has(CAN_WRITE_GLOBAL)
    with pytest.raises(PermissionError) as exc:
        cl._enforce_global_write(user_sess, op="promote_pipeline")
    msg = str(exc.value)
    assert "promote_pipeline" in msg
    assert "alice" in msg
    assert CAN_WRITE_GLOBAL in msg


def test_gate_allows_admin_session_with_capability():
    cl = _layer()
    admin = Session.for_testing("root", is_admin=True)
    assert admin.has(CAN_WRITE_GLOBAL)
    cl._enforce_global_write(admin, op="promote_pipeline")


def test_gate_carve_out_passes_when_session_is_none():
    cl = _layer()
    cl._enforce_global_write(None, op="bootstrap_register")


def test_gate_error_message_format():
    cl = _layer()
    user_sess = Session.for_testing("bob", is_admin=False)
    with pytest.raises(PermissionError) as exc:
        cl._enforce_global_write(user_sess, op="register_datastate")
    msg = str(exc.value)
    assert "register_datastate" in msg
    assert user_sess.session_id in msg
    assert "bob" in msg
    assert CAN_WRITE_GLOBAL in msg


def test_gate_via_public_register_datastate_path():
    cl = _layer()
    user_sess = Session.for_testing("alice", is_admin=False)
    from ._fixtures import text_raw_datastate
    node = cl.register_datastate(text_raw_datastate())
    assert node is not None
    cl2 = _layer()
    cl2.register_datastate(text_raw_datastate(), session=user_sess)
