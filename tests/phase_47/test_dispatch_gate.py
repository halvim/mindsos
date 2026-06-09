"""Phase 47 — L4 dispatch: CapacityContext builder + write-body gate.

Covers ADR-0175/0170: ``L4Dispatcher`` builds a typed CapacityContext for
the read path, and refuses to invoke a write-body (zero-output capacity)
when the session lacks ``CAN_WRITE_GLOBAL``. The write-body is synthetic
(PB-D) — Phase 47 has no production write-body-under-session traffic.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capabilities import CAN_WRITE_GLOBAL
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.context import CapacityContext
from mindsos_capacity.exceptions import CapabilityDeniedError
from mindsos_capacity.identifiers import CATEGORY_CONSOLIDATE, CATEGORY_PLANNING, capacity_iri
from mindsos_capacity.write_outcome import WriteResult
from mindsos_capacity.builtins.planning_v0 import DS_MAPPING_RESULT, DS_PLAN, install_planning_v0

from mindsos_intelligence.dispatch import L4Dispatcher, required_capability_for


class _FakeSession:
    def __init__(self, caps):
        self.session_id = "s-1"
        self.user_id = "u-1"
        self.actor_role = "user"
        self.capabilities = set(caps)

    def has(self, capability: str) -> bool:
        return capability in self.capabilities


def _write_body(**kwargs):
    return WriteResult(
        iri="node:x",
        role="problem_trace",
        scope="global",
        written_at=datetime.now(timezone.utc),
    )


def _layer_with_synthetic_write():
    layer = CapacityLayer()
    layer.register_capacity(
        Capacity(
            name="synthetic_write",
            category=CATEGORY_CONSOLIDATE,
            inputs=(),
            outputs=(),
            implementation=_write_body,
        )
    )
    return layer, capacity_iri(CATEGORY_CONSOLIDATE, "synthetic_write")


def test_required_capability_for_write_vs_read():
    layer, write_iri = _layer_with_synthetic_write()
    install_planning_v0(layer)
    write_decl = layer.get_declaration(write_iri)
    read_decl = layer.get_declaration(
        capacity_iri(CATEGORY_PLANNING, "derive_initial_plan")
    )
    assert required_capability_for(write_decl) == CAN_WRITE_GLOBAL
    assert required_capability_for(read_decl) is None


def test_write_body_denied_without_capability():
    layer, write_iri = _layer_with_synthetic_write()
    dispatcher = L4Dispatcher(layer, session=_FakeSession([]))
    with pytest.raises(CapabilityDeniedError):
        dispatcher.dispatch(write_iri, {})


def test_write_body_permitted_with_capability():
    layer, write_iri = _layer_with_synthetic_write()
    dispatcher = L4Dispatcher(layer, session=_FakeSession([CAN_WRITE_GLOBAL]))
    result = dispatcher.dispatch(write_iri, {})
    assert result.success
    assert isinstance(result.write_outcome, WriteResult)


def test_read_dispatch_builds_capacity_context():
    layer = CapacityLayer()
    install_planning_v0(layer)
    dispatcher = L4Dispatcher(layer, session=_FakeSession([]))

    ctx = dispatcher.build_context(task_iri="task:1", pattern_iri="pattern:1")
    assert isinstance(ctx, CapacityContext)
    assert ctx.session_id == "s-1"
    assert ctx.user_id == "u-1"
    assert ctx.cl is layer
    assert ctx.current_task_iri == "task:1"

    result = dispatcher.dispatch(
        capacity_iri(CATEGORY_PLANNING, "derive_initial_plan"),
        {DS_MAPPING_RESULT: {"task_pattern_iri": "x"}},
    )
    assert result.success
    assert result.outputs[DS_PLAN]["single_milestone"] is True
