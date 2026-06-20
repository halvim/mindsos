"""Phase 30 — invoke() threads session identity into the capacity context.

Migrated at Phase 51 (ADR-0175 §amendment-3): the read path now builds a
typed, frozen ``CapacityContext`` — identity is read by attribute
(``context.user_id`` / ``context.session_id``), not dict key. Without a
session, placeholder defaults apply (parity with the ADR-0180 write
branch). The caller-supplied ``context`` kwarg was removed (clause 2 —
grounded consumer-less).
"""

from __future__ import annotations

from typing import Any, Dict

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    Capacity,
    DataState,
    ShapeDescriptor,
)
from mindsos_capacity.context import CapacityContext

from tests.phase_30._fixtures import DS_INPUT_IRI, DS_OUTPUT_IRI, build_session


def _build_context_capturing_layer():
    """A layer with a capacity that records the context it was passed."""
    from mindsos_capacity import CapacityLayer

    captured: Dict[str, Any] = {}

    def _impl(**kw: Any) -> Dict[str, str]:
        captured["context"] = kw.get("context")
        return {DS_OUTPUT_IRI: "ok"}

    cap = Capacity(
        name="test.context",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        implementation=_impl,
    )
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl.register_datastate(
        DataState(
            name="test.input",
            shape=ShapeDescriptor.scalar("str", opaque_tag="test.input"),
        ),
        allow_new_realm=True,
    )
    cl.register_datastate(
        DataState(
            name="test.output",
            shape=ShapeDescriptor.scalar("str", opaque_tag="test.output"),
        ),
        allow_new_realm=True,
    )
    cl.register_capacity(cap)
    return cl, cap, captured


def test_invoke_with_session_stamps_identity_on_context():
    cl, cap, captured = _build_context_capturing_layer()
    sess = build_session("alice")
    cl.invoke(cap.iri, inputs={DS_INPUT_IRI: "x"}, session=sess)
    ctx = captured["context"]
    assert isinstance(ctx, CapacityContext)
    assert ctx.user_id == "alice"
    assert ctx.session_id == "test-session-alice"


def test_invoke_without_session_uses_placeholder_identity():
    """No session → placeholder defaults (ADR-0175 §am-3 clause 1 —
    parity with the ADR-0180 write branch's ``getattr`` defaults)."""
    cl, cap, captured = _build_context_capturing_layer()
    cl.invoke(cap.iri, inputs={DS_INPUT_IRI: "x"})
    ctx = captured["context"]
    assert isinstance(ctx, CapacityContext)
    assert ctx.user_id == "user"
    assert ctx.session_id == "session"


def test_read_body_context_is_frozen_and_unprivileged():
    """Read bodies get no write capability and an immutable context."""
    import pytest

    cl, cap, captured = _build_context_capturing_layer()
    cl.invoke(cap.iri, inputs={DS_INPUT_IRI: "x"}, session=build_session("alice"))
    ctx = captured["context"]
    assert ctx.writeable is None
    with pytest.raises(Exception):
        ctx.user_id = "mallory"  # frozen dataclass
