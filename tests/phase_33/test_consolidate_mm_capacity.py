"""Phase 33 — ``capacity:consolidate:mm`` registration + stub-path behavior."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CATEGORY_CONSOLIDATE,
    CapacityLayer,
    DS_MM_COMPOSITE_INSTANCE,
    WriteHandleNotWiredError,
    build_consolidate_mm,
    install_consolidate_capacities,
    mm_composite_datastates,
)
from mindsos_capacity.identifiers import capacity_iri, datastate_iri
from tests.phase_33._fixtures import build_session_with_caps


# ── Static surface ────────────────────────────────────────────────────


def test_consolidate_mm_iri_form():
    """ADR-0145 §Impl line 75: capacity:consolidate:mm verbatim."""
    cap = build_consolidate_mm()
    assert cap.iri == "capacity:consolidate:mm"
    assert cap.iri == capacity_iri(CATEGORY_CONSOLIDATE, "mm")


def test_consolidate_mm_outputs_empty_terminator():
    """R2 PB-K: write capacities are pipeline terminators (outputs=())."""
    cap = build_consolidate_mm()
    assert cap.outputs == ()


def test_consolidate_mm_inputs_placeholder():
    """R1 PB-B: input is placeholder DataState (opaque shape)."""
    cap = build_consolidate_mm()
    assert cap.inputs == (DS_MM_COMPOSITE_INSTANCE,)
    assert DS_MM_COMPOSITE_INSTANCE == datastate_iri("mm.composite_instance")


def test_mm_composite_datastates_single_member_opaque():
    states = mm_composite_datastates()
    assert len(states) == 1
    assert states[0].shape.kind == "opaque"
    assert states[0].shape.opaque_tag == "mm.composite_instance"
    assert states[0].provenance_category == CATEGORY_CONSOLIDATE


# ── Registration ──────────────────────────────────────────────────────


def test_install_consolidate_capacities_idempotent_none_present():
    layer = CapacityLayer()
    install_consolidate_capacities(layer)
    decls = layer.iter_declarations()
    assert len(decls) == 1
    assert decls[0].iri == "capacity:consolidate:mm"


def test_install_consolidate_capacities_idempotent_all_present():
    """Second call is no-op (silent return)."""
    layer = CapacityLayer()
    install_consolidate_capacities(layer)
    install_consolidate_capacities(layer)  # no raise
    assert len(layer.iter_declarations()) == 1


def test_install_consolidate_capacities_partial_state_raises():
    """Phase 31 partial-state-detection precedent."""
    from mindsos_capacity import CapacityRegistrationError

    layer = CapacityLayer()
    # Register the DataState but not the capacity → partial.
    for ds in mm_composite_datastates():
        layer.register_datastate(ds)
    with pytest.raises(CapacityRegistrationError, match="partial install state"):
        install_consolidate_capacities(layer)


# ── Stub-path invocation (envelope success=False + error=...) ─────────


def test_consolidate_mm_session_none_yields_value_error_via_envelope():
    """scope='local' + session=None → KL.writeable raises ValueError."""
    layer = CapacityLayer()
    install_consolidate_capacities(layer)
    result = layer.invoke(
        "capacity:consolidate:mm",
        {DS_MM_COMPOSITE_INSTANCE: "placeholder"},
        session=None,
        task_id="T1",
    )
    assert result.success is False
    assert isinstance(result.error, ValueError)


def test_consolidate_mm_with_session_yields_writehandle_not_wired():
    """session present → KL.writeable returns handle → graph() raises."""
    sess = build_session_with_caps("alice", frozenset({"CAN_WRITE_GLOBAL"}))
    layer = CapacityLayer()
    install_consolidate_capacities(layer)
    result = layer.invoke(
        "capacity:consolidate:mm",
        {DS_MM_COMPOSITE_INSTANCE: "placeholder"},
        session=sess,
        task_id="T2",
    )
    assert result.success is False
    assert isinstance(result.error, WriteHandleNotWiredError)


def test_consolidate_mm_emits_problem_trace_on_failure():
    """Phase 30 ProblemTraceSink fires on body raise."""
    sess = build_session_with_caps("alice", frozenset({"CAN_WRITE_GLOBAL"}))
    layer = CapacityLayer()
    install_consolidate_capacities(layer)
    layer.invoke(
        "capacity:consolidate:mm",
        {DS_MM_COMPOSITE_INSTANCE: "placeholder"},
        session=sess,
        task_id="T3",
    )
    recs = layer.problem_trace.records()
    assert len(recs) == 1
    assert recs[0].task_id == "T3"
    assert recs[0].error_kind == "exception:WriteHandleNotWiredError"
    assert recs[0].capacity_iri == "capacity:consolidate:mm"
