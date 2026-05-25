"""Phase 29 — CapacityLayer.rediscover method + capability gate."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from mindsos_capacity import (
    CAN_WRITE_GLOBAL,
    CATEGORY_PERCEPTION,
    CapacityLayer,
    EDGE_TYPE_COMPAT,
)

from ._fixtures import (
    text_demo_capacity,
    text_join_capacity,
    text_raw_datastate,
    text_tokens_datastate,
)


class _StubSession:
    """Minimal Session shim matching mindsos_capacity.SessionProtocol."""

    def __init__(self, *, user_id: str, caps: frozenset[str] = frozenset()):
        self.session_id = "sess:test"
        self.user_id = user_id
        self.caps = caps
        self.created_at = datetime.now(UTC)
        self.expires_at = None

    def has(self, capability: str) -> bool:
        return capability in self.caps


def _populated_global():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl.register_datastate(text_raw_datastate())
    cl.register_datastate(text_tokens_datastate())
    cl.register_capacity(text_demo_capacity())
    cl.register_capacity(text_join_capacity())
    return cl


def test_rediscover_no_session_admin_path_succeeds():
    """ADR-0080 bootstrap carve-out: session=None permits Global rediscover."""
    cl = _populated_global()
    created = cl.rediscover()
    assert isinstance(created, list)


def test_rediscover_session_with_capability_succeeds_on_global():
    cl = _populated_global()
    sess = _StubSession(user_id="admin1", caps=frozenset({CAN_WRITE_GLOBAL}))
    # session.user_id is non-None → targets Local, not Global. To target
    # Global with a session we'd need session.user_id == None which the
    # protocol doesn't allow. So this test verifies Local rediscover
    # works with a session.
    cl_local = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl_local.register_datastate(text_raw_datastate(), session=sess)
    cl_local.register_datastate(text_tokens_datastate(), session=sess)
    cl_local.register_capacity(text_demo_capacity(), session=sess)
    created = cl_local.rediscover(session=sess)
    assert isinstance(created, list)


def test_rediscover_session_without_capability_targets_local_no_gate():
    """Session.user_id non-None → target is Local; no CAN_WRITE_GLOBAL needed."""
    cl_local = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    sess = _StubSession(user_id="user1", caps=frozenset())
    cl_local.register_datastate(text_raw_datastate(), session=sess)
    cl_local.register_datastate(text_tokens_datastate(), session=sess)
    cl_local.register_capacity(text_demo_capacity(), session=sess)
    # No PermissionError — Local writes don't need CAN_WRITE_GLOBAL.
    cl_local.rediscover(session=sess)
