"""Phase 31 — __init__.py export slate stability.

Phase 31 originally added +2 exports (ResidentSubscription +
ResidentError) → 97 total. **Phase 41 (ADR-0155) retires both** when
monitor lifecycle relocates to the L4 substrate; this sentinel is
flipped present→absent at the target phase per
``[[feedback-parity-test-sentinel-flip-at-target-phase]]``.
"""

from __future__ import annotations

import mindsos_capacity


# Retired in Phase 41 (ADR-0155) — flipped from present to absent.
PHASE_31_RETIRED_EXPORTS = {
    "ResidentSubscription",
    "ResidentError",
}


def test_phase_31_resident_exports_retired():
    """Both Phase 31 resident exports are absent after the ADR-0155 retirement."""
    present = PHASE_31_RETIRED_EXPORTS & set(mindsos_capacity.__all__)
    assert not present, f"Phase 41 should have retired: {sorted(present)}"


def test_each_retired_resident_export_unresolvable():
    for name in PHASE_31_RETIRED_EXPORTS:
        assert not hasattr(mindsos_capacity, name), (
            f"{name} still resolvable after Phase 41 retirement (ADR-0155)"
        )


def test_phase_42_export_count_is_117():
    """Count-equals sentinel — 95 (P30) -> 97 (P31) -> 110 (P33) ->
    114 (P40) -> 112 (P41) -> 117 (P42). Phase 42 retires 6 type-compat/
    discovery exports per ADR-0156 and adds 11 ADR-0159 contract exports.
    """
    assert len(mindsos_capacity.__all__) == 117, (
        f"Expected 117 exports at Phase 42; found {len(mindsos_capacity.__all__)}"
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
    assert mindsos_capacity.__version__ == "0.0.0+phase44"
