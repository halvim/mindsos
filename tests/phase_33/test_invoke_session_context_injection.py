"""Phase 33 → Phase 51 — the capacity context carries NO Session object.

Original contract (ADR-0146 §amendment-1 clause 2): ``invoke`` injected
the Session into ``context["session"]`` so write bodies could gate via
``session.has(cap)``. That write-side need was superseded at Phase 48 by
the ADR-0180 pre-authorized ``writeable`` capability, and the read-path
dict (the injection's only remaining carrier) was retired at Phase 51
(ADR-0175 §amendment-3 clause 3). This file now pins the NEW invariant:
the typed ``CapacityContext`` is authorization-free — it carries a
narrowed capability, never a principal (ADR-0170).
"""

from __future__ import annotations

import dataclasses
from typing import Any

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    Capacity,
    CapacityLayer,
    DataState,
    ShapeDescriptor,
)
from mindsos_capacity.context import CapacityContext
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


def test_context_carries_no_session_object():
    """ADR-0170: no principal on the context — by field roster, not just
    by value. A ``session`` field reappearing is a contract break."""
    layer, cap, captured = _build_context_capturing_layer()
    sess = build_session_with_caps("alice", frozenset({"CAN_WRITE_GLOBAL"}))
    layer.invoke(cap.iri, {DS_PROBE: "x"}, session=sess)
    ctx = captured["context"]
    assert isinstance(ctx, CapacityContext)
    field_names = {f.name for f in dataclasses.fields(ctx)}
    assert "session" not in field_names
    # Identity is threaded as plain fields (Phase 30 invariants, attribute form):
    assert ctx.user_id == "alice"
    assert ctx.session_id == "test-session-alice"


def test_session_capabilities_do_not_leak_to_read_context():
    """A capability-rich session grants a read body nothing: ``writeable``
    stays None regardless of session capabilities."""
    layer, cap, captured = _build_context_capturing_layer()
    sess = build_session_with_caps("alice", frozenset({"CAN_WRITE_GLOBAL"}))
    layer.invoke(cap.iri, {DS_PROBE: "x"}, session=sess)
    assert captured["context"].writeable is None
