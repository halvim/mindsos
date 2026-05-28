"""Phase 31 — __init__.py export slate stability.

Per R2 PB-20 + R3 PB-31: Phase 30 ended at 95 exports; Phase 31 adds
+2 (ResidentSubscription + ResidentError) → 97 total. Names must
include the 2 Phase 31 additions.

NO Phase-32-forward forbidden-export sentinel (R2 PB-20 lock — Phase
32 is integration, no NEW exports expected). Count-equals-97 sentinel
ships — it's load-bearing for Phase 33 lift detection.
"""

from __future__ import annotations

import mindsos_capacity


PHASE_31_NEW_EXPORTS = {
    "ResidentSubscription",
    "ResidentError",
}


def test_all_phase_31_exports_present():
    missing = PHASE_31_NEW_EXPORTS - set(mindsos_capacity.__all__)
    assert not missing, f"Phase 31 missing exports: {sorted(missing)}"


def test_each_phase_31_export_resolves_to_real_object():
    for name in PHASE_31_NEW_EXPORTS:
        assert hasattr(mindsos_capacity, name), f"{name} missing from module"
        assert getattr(mindsos_capacity, name) is not None


def test_phase_31_export_count_is_110():
    """Count-equals sentinel — Phase 32 unchanged at 97; Phase 33 lifts
    to 110 per ADR-0146 §Implementation (Phase 33): +13 new exports
    (WriteResult, WriteOutcome, WriteHandleNotWiredError,
    CapabilityDeniedError, CATEGORY_CONSOLIDATE,
    DS_MM_COMPOSITE_INSTANCE, DS_PROBLEM_TRACE_RECORD,
    mm_composite_datastates, problem_trace_datastates,
    build_consolidate_mm, build_trace_problem,
    install_consolidate_capacities, install_trace_capacities).
    """
    assert len(mindsos_capacity.__all__) == 110, (
        f"Expected 110 exports at Phase 33; found {len(mindsos_capacity.__all__)}"
    )


def test_phase_30_exports_remain_intact():
    """No Phase 30 export was dropped at Phase 31."""
    phase_30_set = {
        "InvocationResult",
        "call_capacity",
        "invoke",
        "ProblemTraceRecord",
        "ProblemTraceSink",
        "emit_problem_trace",
        "Pipeline",
        "PipelineStep",
        "find_pipeline",
        "PipelineNotFoundError",
        "ProblemTraceError",
    }
    missing = phase_30_set - set(mindsos_capacity.__all__)
    assert not missing, f"Phase 30 exports dropped at Phase 31: {sorted(missing)}"


def test_version_bumped_to_phase_34():
    assert mindsos_capacity.__version__ == "0.0.0+phase38"
