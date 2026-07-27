"""Phase 33 — ``capacity:trace:problem`` registration + cap-denial + invocation.

3 of 4 invocation tests REPURPOSED at Phase 34 (R4 §am-impl-5):
handle-not-wired sentinels flip to success-path. Cap-denial STAYS
(R0 PB-6 — cap-denial keeps raising; clause 1 open). Shape sentinel
flipped opaque → record per R4 §am-impl-2.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CATEGORY_TRACE,
    CAN_WRITE_GLOBAL,
    CapabilityDeniedError,
    CapacityLayer,
    DS_PROBLEM_TRACE_RECORD,
    WriteResult,
    build_trace_problem,
    install_trace_capacities,
    problem_trace_datastates,
)
from mindsos_capacity.identifiers import capacity_iri, datastate_iri
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_knowledge import KnowledgeLayer
from tests.phase_33._fixtures import build_session_with_caps


# ── Static surface ────────────────────────────────────────────────────


def test_trace_problem_iri_form():
    """ADR-0145 §Impl line 75: capacity:trace:problem verbatim."""
    cap = build_trace_problem()
    assert cap.iri == "capacity:trace:problem"
    assert cap.iri == capacity_iri(CATEGORY_TRACE, "problem")


def test_trace_problem_outputs_empty_terminator():
    cap = build_trace_problem()
    assert cap.outputs == ()


def test_trace_problem_inputs_record():
    cap = build_trace_problem()
    assert cap.inputs == (DS_PROBLEM_TRACE_RECORD,)
    assert DS_PROBLEM_TRACE_RECORD == datastate_iri("problem_trace.record")


def test_problem_trace_datastates_single_member_record():
    """Phase 34 R4 §am-impl-2: shape.kind flipped opaque → record."""
    states = problem_trace_datastates()
    assert len(states) == 1
    assert states[0].shape.kind == "record"
    assert states[0].shape.opaque_tag == "problem_trace.record"
    assert dict(states[0].shape.fields) == {
        "trace_id": "str",
        "value": "Any",
    }
    assert states[0].provenance_category == CATEGORY_TRACE


# ── Registration ──────────────────────────────────────────────────────


def test_install_trace_capacities_idempotent_none_present():
    layer = CapacityLayer()
    install_trace_capacities(layer)
    decls = layer.iter_declarations()
    assert len(decls) == 1
    assert decls[0].iri == "capacity:trace:problem"


def test_install_trace_capacities_idempotent_all_present():
    layer = CapacityLayer()
    install_trace_capacities(layer)
    install_trace_capacities(layer)
    assert len(layer.iter_declarations()) == 1


def test_install_trace_capacities_partial_state_raises():
    from mindsos_capacity import CapacityRegistrationError

    layer = CapacityLayer()
    for ds in problem_trace_datastates():
        layer.register_datastate(ds)
    with pytest.raises(CapacityRegistrationError, match="partial install state"):
        install_trace_capacities(layer)


# ── Cap-denial path (STAYS per R0 PB-6 — clause 1 open) ──────────────


def test_trace_problem_cap_denied_when_session_lacks_can_write_global():
    """session present without CAN_WRITE_GLOBAL → CapabilityDeniedError.

    Phase 48 (ADR-0180): the global-scope gate now fires at call-time
    inside ``context.writeable`` (built by L4Dispatcher), not in the body.
    The denial surfaces enveloped in the result.
    """
    sess = build_session_with_caps("non_admin", frozenset())  # empty caps
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_trace_capacities(layer)
    dispatcher = L4Dispatcher(layer, session=sess, kl=kl)
    result = dispatcher.dispatch(
        "capacity:trace:problem",
        {DS_PROBLEM_TRACE_RECORD: {"trace_id": "t1", "value": "err"}},
        request_id="T1",
    )
    assert result.success is False
    assert isinstance(result.error, CapabilityDeniedError)


# ── Success paths (Phase 48 L4Dispatcher path) ────────────────────────


def test_trace_problem_session_with_cap_succeeds():
    """Cap-granted session → global write succeeds through context.writeable."""
    sess = build_session_with_caps("admin", frozenset({CAN_WRITE_GLOBAL}))
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_trace_capacities(layer)
    dispatcher = L4Dispatcher(layer, session=sess, kl=kl)
    result = dispatcher.dispatch(
        "capacity:trace:problem",
        {DS_PROBLEM_TRACE_RECORD: {"trace_id": "t1", "value": "boom"}},
        request_id="T2",
    )
    assert result.success is True
    assert result.error is None
    assert isinstance(result.write_outcome, WriteResult)
    assert result.write_outcome.iri == "problem-trace-v1:entry:t1"
    assert result.write_outcome.role == "problem-trace"
    assert result.write_outcome.scope == "global"


def test_trace_problem_session_none_skips_gate_per_adr_0080_and_succeeds():
    """ADR-0080: session=None permits Global writes (bootstrap carve-out).
    The call-time gate skips when session is None; the write succeeds."""
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_trace_capacities(layer)
    dispatcher = L4Dispatcher(layer, session=None, kl=kl)
    result = dispatcher.dispatch(
        "capacity:trace:problem",
        {DS_PROBLEM_TRACE_RECORD: {"trace_id": "t-boot", "value": "init"}},
        request_id="T3",
    )
    assert result.success is True
    assert isinstance(result.write_outcome, WriteResult)
    assert result.write_outcome.iri == "problem-trace-v1:entry:t-boot"


def test_trace_problem_success_emits_no_problem_trace():
    """No problem-trace fires on a successful write (Phase 48 L4Dispatcher)."""
    sess = build_session_with_caps("admin", frozenset({CAN_WRITE_GLOBAL}))
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_trace_capacities(layer)
    dispatcher = L4Dispatcher(layer, session=sess, kl=kl)
    dispatcher.dispatch(
        "capacity:trace:problem",
        {DS_PROBLEM_TRACE_RECORD: {"trace_id": "t1", "value": "ok"}},
        request_id="T4",
    )
    recs = layer.problem_trace.records()
    assert len(recs) == 0
