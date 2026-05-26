"""Phase 30 — __init__.py export slate stability.

Per R2 PB-31(a) + R4 PB-50(a): Phase 29 ended at 84 exports; Phase 30
adds +11 → 95 total. Names must include the 11 Phase 30 additions.
"""

from __future__ import annotations

import mindsos_capacity


PHASE_30_NEW_EXPORTS = {
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


def test_all_phase_30_exports_present():
    missing = PHASE_30_NEW_EXPORTS - set(mindsos_capacity.__all__)
    assert not missing, f"Phase 30 missing exports: {sorted(missing)}"


def test_each_phase_30_export_resolves_to_real_object():
    for name in PHASE_30_NEW_EXPORTS:
        assert hasattr(mindsos_capacity, name), f"{name} missing from module"
        assert getattr(mindsos_capacity, name) is not None


def test_version_bumped_to_phase_32():
    # Phase 32 sentinel-flip: Phase 31 shipped this as
    # ``test_version_bumped_to_phase_31`` asserting ``0.0.0+phase31``.
    # Phase 32 bumps the literal; sentinel flips in place per
    # [[feedback-parity-test-sentinel-flip-at-target-phase]] + the
    # export-slate sentinel-flip class (B-30-T1 / B-31-T2 lessons).
    # File stays under tests/phase_30/ because it's a Phase 30
    # export-stability check that the version moves forward correctly
    # at each subsequent phase.
    assert mindsos_capacity.__version__ == "0.0.0+phase32"


def test_phase_29_exports_remain_intact():
    """No Phase 29 export was dropped at Phase 30."""
    phase_29_set = {
        "Capacity",
        "Monitor",
        "Adapter",
        "_CapacityBase",
        "DataState",
        "ShapeDescriptor",
        "CapacityLayer",
        "CapacityLayerView",
        "SuccessorHop",
        "discover_for_capacity",
        "discover_for_datastate",
        "rediscover_all",
        "create_global",
        "create_local",
        "CAN_WRITE_GLOBAL",
        "SessionProtocol",
        "schema_for_role",
        "DiscoveryFailedError",
        "ConstraintViolationError",
    }
    missing = phase_29_set - set(mindsos_capacity.__all__)
    assert not missing, f"Phase 29 exports dropped at Phase 30: {sorted(missing)}"
