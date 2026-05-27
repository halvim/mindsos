"""Phase 33 — ``capacity:consolidate:mm`` registration + invocation behavior.

5 tests repurposed at Phase 34 (R4 §am-impl-5) — the handle-not-wired
sentinels flip to success-path assertions now that Phase 34 wired
``KLWriteHandle.graph()`` + ``mint_iri()`` + ``write_and_validate()``.
Cap-denial does NOT apply (consolidate has no cap gate); session-None
ValueError sentinel STAYS (writeable still raises on scope='local').
Shape sentinel flipped opaque → record per R4 §am-impl-2.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CATEGORY_CONSOLIDATE,
    CapacityLayer,
    DS_MM_COMPOSITE_INSTANCE,
    WriteResult,
    build_consolidate_mm,
    install_consolidate_capacities,
    mm_composite_datastates,
)
from mindsos_capacity.identifiers import capacity_iri, datastate_iri
from mindsos_knowledge import KnowledgeLayer
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


def test_consolidate_mm_inputs_record():
    """R2 PB-A: input tightened from opaque to record at Phase 34."""
    cap = build_consolidate_mm()
    assert cap.inputs == (DS_MM_COMPOSITE_INSTANCE,)
    assert DS_MM_COMPOSITE_INSTANCE == datastate_iri("mm.composite_instance")


def test_mm_composite_datastates_single_member_record():
    """Phase 34 R4 §am-impl-2: shape.kind flipped opaque → record."""
    states = mm_composite_datastates()
    assert len(states) == 1
    assert states[0].shape.kind == "record"
    assert states[0].shape.opaque_tag == "mm.composite_instance"
    assert dict(states[0].shape.fields) == {
        "memory_id": "str",
        "value": "Any",
    }
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


# ── Invocation paths ──────────────────────────────────────────────────


def test_consolidate_mm_session_none_yields_value_error_via_envelope():
    """STAYS — scope='local' + session=None → KL.writeable raises ValueError.

    Phase 34 unchanged: writeable() pre-emptively rejects None session
    on Local writes (ADR-0080 carve-out is Global-only).
    """
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_consolidate_capacities(layer)
    result = layer.invoke(
        "capacity:consolidate:mm",
        {DS_MM_COMPOSITE_INSTANCE: {"memory_id": "m1", "value": "test"}},
        session=None,
        task_id="T1",
    )
    assert result.success is False
    assert isinstance(result.error, ValueError)


def test_consolidate_mm_with_session_succeeds_with_write_outcome():
    """REPURPOSED — Phase 34 wired graph()+mint_iri()+write_and_validate.

    Phase 33 asserted ``WriteHandleNotWiredError``; Phase 34 asserts
    success + populated ``write_outcome``.
    """
    sess = build_session_with_caps("alice", frozenset({"CAN_WRITE_GLOBAL"}))
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_consolidate_capacities(layer)
    result = layer.invoke(
        "capacity:consolidate:mm",
        {DS_MM_COMPOSITE_INSTANCE: {"memory_id": "m1", "value": "remember this"}},
        session=sess,
        task_id="T2",
    )
    assert result.success is True
    assert result.error is None
    assert isinstance(result.write_outcome, WriteResult)
    assert result.write_outcome.iri == "memories-v1:memory:alice:m1"
    assert result.write_outcome.role == "memories"
    assert result.write_outcome.scope == "local"


def test_consolidate_mm_success_emits_no_problem_trace():
    """REPURPOSED — Phase 33 asserted trace fired on raise; Phase 34
    asserts NO trace fires on successful write (R4 §am-impl-5)."""
    sess = build_session_with_caps("alice", frozenset({"CAN_WRITE_GLOBAL"}))
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_consolidate_capacities(layer)
    layer.invoke(
        "capacity:consolidate:mm",
        {DS_MM_COMPOSITE_INSTANCE: {"memory_id": "m1", "value": "ok"}},
        session=sess,
        task_id="T3",
    )
    recs = layer.problem_trace.records()
    assert len(recs) == 0
