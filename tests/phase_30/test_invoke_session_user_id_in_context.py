"""Phase 30 — invoke() injects session_user_id + session_id into context.

Per CapacityLayer.invoke contract: when session is supplied, the
session's user_id is injected into context['session_user_id'] for
provenance-stamping capacities. Caller-set keys must not be overwritten.
"""

from __future__ import annotations

from typing import Any, Dict

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    Capacity,
    DataState,
    ShapeDescriptor,
)

from tests.phase_30._fixtures import DS_INPUT_IRI, DS_OUTPUT_IRI, build_session


def _build_context_capturing_layer():
    """A layer with a capacity that records the context it was passed."""
    from mindsos_capacity import CapacityLayer

    captured: Dict[str, Any] = {}

    def _impl(**kw: Any) -> Dict[str, str]:
        ctx = kw.get("context") or {}
        captured["context"] = dict(ctx)
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


def test_invoke_with_session_stamps_user_id_into_context():
    cl, cap, captured = _build_context_capturing_layer()
    sess = build_session("alice")
    cl.invoke(cap.iri, inputs={DS_INPUT_IRI: "x"}, session=sess)
    assert captured["context"]["session_user_id"] == "alice"
    assert captured["context"]["session_id"] == "test-session-alice"


def test_invoke_without_session_omits_session_keys():
    cl, cap, captured = _build_context_capturing_layer()
    cl.invoke(cap.iri, inputs={DS_INPUT_IRI: "x"})
    ctx = captured["context"]
    assert "session_user_id" not in ctx
    assert "session_id" not in ctx


def test_invoke_does_not_overwrite_caller_set_context_keys():
    cl, cap, captured = _build_context_capturing_layer()
    sess = build_session("alice")
    cl.invoke(
        cap.iri,
        inputs={DS_INPUT_IRI: "x"},
        session=sess,
        context={"session_user_id": "bob"},
    )
    assert captured["context"]["session_user_id"] == "bob"
