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
from mindsos_intelligence.dispatch import L4Dispatcher
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
        "episode_id": "str",
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
    """scope='local' + session=None → KL.writeable raises ValueError.

    Phase 48 (ADR-0180): dispatched via L4Dispatcher; the gated
    ``context.writeable`` calls ``kl.writeable(None, …, 'local')`` which
    rejects a None session for Local writes (ADR-0080 carve-out is
    Global-only). The ValueError surfaces enveloped in the result.
    """
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_consolidate_capacities(layer)
    dispatcher = L4Dispatcher(layer, session=None, kl=kl)
    result = dispatcher.dispatch(
        "capacity:consolidate:mm",
        {DS_MM_COMPOSITE_INSTANCE: {"episode_id": "e1", "value": "test"}},
        request_id="T1",
    )
    assert result.success is False
    assert isinstance(result.error, ValueError)


def test_consolidate_mm_with_session_succeeds_with_write_outcome():
    """Phase 48 (ADR-0180): dispatched via L4Dispatcher; the body writes
    the Episode through the pre-authorized ``context.writeable`` capability
    (Local scope — no CAN_WRITE_GLOBAL required, PB-10)."""
    sess = build_session_with_caps("alice", frozenset())
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_consolidate_capacities(layer)
    dispatcher = L4Dispatcher(layer, session=sess, kl=kl)
    result = dispatcher.dispatch(
        "capacity:consolidate:mm",
        {DS_MM_COMPOSITE_INSTANCE: {"episode_id": "e1", "value": "remember this"}},
        request_id="T2",
    )
    assert result.success is True
    assert result.error is None
    assert isinstance(result.write_outcome, WriteResult)
    assert result.write_outcome.iri == "episodic-memories-v1:episode:alice:e1"
    assert result.write_outcome.role == "episodic_memories"
    assert result.write_outcome.scope == "local"


def test_consolidate_mm_success_emits_no_problem_trace():
    """No problem-trace fires on a successful write (Phase 48 L4Dispatcher
    path; sink = layer.problem_trace)."""
    sess = build_session_with_caps("alice", frozenset())
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_consolidate_capacities(layer)
    dispatcher = L4Dispatcher(layer, session=sess, kl=kl)
    dispatcher.dispatch(
        "capacity:consolidate:mm",
        {DS_MM_COMPOSITE_INSTANCE: {"episode_id": "e1", "value": "ok"}},
        request_id="T3",
    )
    recs = layer.problem_trace.records()
    assert len(recs) == 0
