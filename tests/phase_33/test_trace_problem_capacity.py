"""Phase 33 — ``capacity:trace:problem`` registration + cap-denial + stub-path."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CATEGORY_TRACE,
    CAN_WRITE_GLOBAL,
    CapabilityDeniedError,
    CapacityLayer,
    DS_PROBLEM_TRACE_RECORD,
    WriteHandleNotWiredError,
    build_trace_problem,
    install_trace_capacities,
    problem_trace_datastates,
)
from mindsos_capacity.identifiers import capacity_iri, datastate_iri
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


def test_trace_problem_inputs_placeholder():
    cap = build_trace_problem()
    assert cap.inputs == (DS_PROBLEM_TRACE_RECORD,)
    assert DS_PROBLEM_TRACE_RECORD == datastate_iri("problem_trace.record")


def test_problem_trace_datastates_single_member_opaque():
    states = problem_trace_datastates()
    assert len(states) == 1
    assert states[0].shape.kind == "opaque"
    assert states[0].shape.opaque_tag == "problem_trace.record"
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


# ── Cap-denial path ───────────────────────────────────────────────────


def test_trace_problem_cap_denied_when_session_lacks_can_write_global():
    """Session present without CAN_WRITE_GLOBAL → CapabilityDeniedError."""
    sess = build_session_with_caps("non_admin", frozenset())  # empty caps
    layer = CapacityLayer()
    install_trace_capacities(layer)
    result = layer.invoke(
        "capacity:trace:problem",
        {DS_PROBLEM_TRACE_RECORD: "placeholder"},
        session=sess,
        task_id="T1",
    )
    assert result.success is False
    assert isinstance(result.error, CapabilityDeniedError)


def test_trace_problem_session_with_cap_reaches_handle_then_writehandle_not_wired():
    """Cap-granted session passes the gate → handle's graph() raises."""
    sess = build_session_with_caps("admin", frozenset({CAN_WRITE_GLOBAL}))
    layer = CapacityLayer()
    install_trace_capacities(layer)
    result = layer.invoke(
        "capacity:trace:problem",
        {DS_PROBLEM_TRACE_RECORD: "placeholder"},
        session=sess,
        task_id="T2",
    )
    assert result.success is False
    assert isinstance(result.error, WriteHandleNotWiredError)


def test_trace_problem_session_none_skips_gate_per_adr_0080():
    """ADR-0080: session=None permits Global writes (bootstrap carve-out)."""
    layer = CapacityLayer()
    install_trace_capacities(layer)
    result = layer.invoke(
        "capacity:trace:problem",
        {DS_PROBLEM_TRACE_RECORD: "placeholder"},
        session=None,
        task_id="T3",
    )
    # No cap-denied; reaches handle.graph() and raises WriteHandleNotWiredError.
    assert result.success is False
    assert isinstance(result.error, WriteHandleNotWiredError)


def test_trace_problem_emits_problem_trace_on_failure():
    sess = build_session_with_caps("admin", frozenset({CAN_WRITE_GLOBAL}))
    layer = CapacityLayer()
    install_trace_capacities(layer)
    layer.invoke(
        "capacity:trace:problem",
        {DS_PROBLEM_TRACE_RECORD: "placeholder"},
        session=sess,
        task_id="T4",
    )
    recs = layer.problem_trace.records()
    assert len(recs) == 1
    assert recs[0].error_kind == "exception:WriteHandleNotWiredError"
