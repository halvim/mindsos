"""Phase 47/48 — L4 dispatch: CapacityContext builder + scope-aware write gate.

Covers ADR-0175/0170/0180: ``L4Dispatcher`` builds a typed CapacityContext
for the read path and injects a **pre-authorized ``writeable`` capability**
for write-bodies. Phase 48 (ADR-0180) replaced the Phase-47 blanket
pre-gate (which demanded ``CAN_WRITE_GLOBAL`` for any write-body and so
over-restricted Local writes) with a **call-time, scope-aware** gate inside
``context.writeable``: Global writes require ``CAN_WRITE_GLOBAL``; Local
writes require nothing. The exception surfaces enveloped in the
``InvocationResult`` (the body calls the gated capability; runtime envelopes).
"""

from __future__ import annotations

from datetime import datetime, timezone

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capabilities import CAN_WRITE_GLOBAL
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.context import CapacityContext
from mindsos_capacity.exceptions import CapabilityDeniedError
from mindsos_capacity.identifiers import CATEGORY_CONSOLIDATE, CATEGORY_PLANNING, capacity_iri
from mindsos_capacity.write_outcome import WriteResult
from mindsos_capacity.builtins.planning_v0 import DS_MAPPING_RESULT, DS_PLAN, install_planning_v0
from mindsos_knowledge import KnowledgeLayer

from mindsos_intelligence.dispatch import L4Dispatcher


class _FakeSession:
    def __init__(self, caps):
        self.session_id = "s-1"
        self.user_id = "u-1"
        self.actor_role = "user"
        self.capabilities = set(caps)

    def has(self, capability: str) -> bool:
        return capability in self.capabilities


def _global_write_body(**kwargs):
    ctx = kwargs["context"]
    ctx.writeable(role="problem-trace", scope="global", version="v1")
    return WriteResult(
        iri="node:x",
        role="problem_trace",
        scope="global",
        written_at=datetime.now(timezone.utc),
    )


def _local_write_body(**kwargs):
    ctx = kwargs["context"]
    ctx.writeable(role="episodic_memories", scope="local", version="v1")
    return WriteResult(
        iri="node:y",
        role="episodic_memories",
        scope="local",
        written_at=datetime.now(timezone.utc),
    )


def _layer_with_write(body, name):
    layer = CapacityLayer()
    layer.register_capacity(
        Capacity(
            name=name,
            category=CATEGORY_CONSOLIDATE,
            inputs=(),
            outputs=(),
            implementation=body,
        )
    )
    return layer, capacity_iri(CATEGORY_CONSOLIDATE, name)


def test_global_write_denied_without_capability():
    layer, write_iri = _layer_with_write(_global_write_body, "synthetic_global_write")
    dispatcher = L4Dispatcher(layer, session=_FakeSession([]), kl=KnowledgeLayer.bootstrap())
    result = dispatcher.dispatch(write_iri, {})
    assert result.success is False
    assert isinstance(result.error, CapabilityDeniedError)


def test_global_write_permitted_with_capability():
    layer, write_iri = _layer_with_write(_global_write_body, "synthetic_global_write")
    dispatcher = L4Dispatcher(
        layer, session=_FakeSession([CAN_WRITE_GLOBAL]), kl=KnowledgeLayer.bootstrap()
    )
    result = dispatcher.dispatch(write_iri, {})
    assert result.success
    assert isinstance(result.write_outcome, WriteResult)


def test_local_write_permitted_without_global_cap():
    # ADR-0180 / PB-10: Local writes need no CAN_WRITE_GLOBAL.
    layer, write_iri = _layer_with_write(_local_write_body, "synthetic_local_write")
    dispatcher = L4Dispatcher(layer, session=_FakeSession([]), kl=KnowledgeLayer.bootstrap())
    result = dispatcher.dispatch(write_iri, {})
    assert result.success
    assert isinstance(result.write_outcome, WriteResult)


def test_read_dispatch_builds_capacity_context():
    layer = CapacityLayer()
    install_planning_v0(layer)
    dispatcher = L4Dispatcher(layer, session=_FakeSession([]))

    ctx = dispatcher.build_context(request_iri="task:1", pattern_iri="pattern:1")
    assert isinstance(ctx, CapacityContext)
    assert ctx.session_id == "s-1"
    assert ctx.user_id == "u-1"
    assert ctx.cl is layer
    assert ctx.current_request_iri == "task:1"

    result = dispatcher.dispatch(
        capacity_iri(CATEGORY_PLANNING, "derive_initial_plan"),
        {DS_MAPPING_RESULT: {"task_pattern_iri": "x"}},
    )
    assert result.success
    assert result.outputs[DS_PLAN]["single_milestone"] is True
