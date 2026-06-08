"""Phase 33 — export-slate forward-anchor sentinel for Phase 34+."""

from __future__ import annotations

import mindsos_capacity


PHASE_33_NEW_EXPORTS = frozenset({
    "WriteResult",
    "WriteOutcome",
    "WriteHandleNotWiredError",
    "CapabilityDeniedError",
    "CATEGORY_CONSOLIDATE",
    "DS_MM_COMPOSITE_INSTANCE",
    "mm_composite_datastates",
    "build_consolidate_mm",
    "install_consolidate_capacities",
    "DS_PROBLEM_TRACE_RECORD",
    "problem_trace_datastates",
    "build_trace_problem",
    "install_trace_capacities",
})


def test_all_phase_33_exports_present():
    missing = PHASE_33_NEW_EXPORTS - set(mindsos_capacity.__all__)
    assert not missing, f"Phase 33 exports missing from __all__: {sorted(missing)}"


def test_each_phase_33_export_resolves_to_real_object():
    for name in PHASE_33_NEW_EXPORTS:
        assert hasattr(mindsos_capacity, name), f"{name} missing from module"
        assert getattr(mindsos_capacity, name) is not None


def test_phase_45_export_count_is_118():
    """Count sentinel — Phase 45 (Rail D, ADR-0162) adds 1 (DreamCapacity): 117 -> 118."""
    assert len(mindsos_capacity.__all__) == 118, (
        f"Expected 118 exports at Phase 45; found {len(mindsos_capacity.__all__)}"
    )


def test_phase_31_resident_exports_retired_at_phase_41():
    """Phase 31's ResidentSubscription / ResidentError were retired in
    Phase 41 (ADR-0155 — monitor lifecycle relocated to L4 substrate)."""
    phase_31_resident_set = {
        "ResidentSubscription",
        "ResidentError",
    }
    present = phase_31_resident_set & set(mindsos_capacity.__all__)
    assert not present, f"Phase 41 should have retired: {sorted(present)}"


def test_kl_write_handle_exported_from_mindsos_knowledge():
    """ADR-0143 stub — handle is L2-located; KL exports it."""
    import mindsos_knowledge
    assert "KLWriteHandle" in mindsos_knowledge.__all__
    assert hasattr(mindsos_knowledge, "KLWriteHandle")
