"""Phase 33 — invoke() injects Session object into context (R2 PB-J).

Verifies ADR-0146 §amendment-1 clause 2: session is reachable from the
capacity body via ``context['session']``. Read-side tests from Phase 30
continue to assert membership (in / not in); the new "session" key is
backward-compatible.
"""

from __future__ import annotations

from typing import Any

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    Capacity,
    CapacityLayer,
    DataState,
    ShapeDescriptor,
)
from mindsos_capacity.identifiers import datastate_iri
from tests.phase_33._fixtures import build_session_with_caps


DS_PROBE = datastate_iri("mm.probe_input")
DS_PROBE_OUT = datastate_iri("mm.probe_output")


def _build_context_capturing_layer():
    captured = {}

    def _impl(**kwargs: Any) -> dict:
        captured["context"] = kwargs.get("context")
        return {DS_PROBE_OUT: "ok"}

    cap = Capacity(
        name="phase33.probe",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_PROBE,),
        outputs=(DS_PROBE_OUT,),
        implementation=_impl,
    )
    layer = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    layer.register_datastate(
        DataState(name="mm.probe_input", shape=ShapeDescriptor.scalar("str"))
    )
    layer.register_datastate(
        DataState(name="mm.probe_output", shape=ShapeDescriptor.scalar("str"))
    )
    layer.register_capacity(cap)
    return layer, cap, captured


def test_invoke_with_session_injects_session_object():
    layer, cap, captured = _build_context_capturing_layer()
    sess = build_session_with_caps("alice", frozenset({"CAN_WRITE_GLOBAL"}))
    layer.invoke(cap.iri, {DS_PROBE: "x"}, session=sess)
    ctx = captured["context"]
    assert ctx["session"] is sess
    # Phase 30 invariants still hold:
    assert ctx["session_user_id"] == "alice"
    assert ctx["session_id"] == "test-session-alice"


def test_invoke_without_session_omits_session_key():
    """ADR-0146 §amendment-1 clause 2: injection only when session is not None."""
    layer, cap, captured = _build_context_capturing_layer()
    layer.invoke(cap.iri, {DS_PROBE: "x"})
    ctx = captured["context"]
    if ctx is not None:
        assert "session" not in ctx
        assert "session_user_id" not in ctx


def test_invoke_does_not_overwrite_caller_set_session_key():
    """setdefault preserves caller intent (Phase 30 pattern)."""
    layer, cap, captured = _build_context_capturing_layer()
    sess = build_session_with_caps("alice", frozenset())
    sentinel = object()
    layer.invoke(
        cap.iri,
        {DS_PROBE: "x"},
        session=sess,
        context={"session": sentinel},
    )
    assert captured["context"]["session"] is sentinel
