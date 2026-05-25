"""Phase 29 — __init__.py export slate.

Two sentinels in this file FLIPPED at Phase 30 (B-30-T1 hotfix):
``test_phase_29_does_not_export_phase_30_surface`` and
``test_phase_29_export_count_around_84``. Phase 30 lifts the
InvocationResult / call_capacity / invoke / ProblemTrace surface per
ADR-0066 §Implementation + ADR-0072 §amendment-1 + ADR-0074
§Implementation footers; the Phase 29 "forbidden surface" set inverts
to a "present-at-Phase-30" assertion, and the count check widens to
the Phase 30 baseline (95). Discipline per
``[[feedback-parity-test-sentinel-flip-at-target-phase]]``.

Original Phase 29 invariants on its own export additions remain
unchanged (``test_phase_29_exports_5_new_names`` +
``test_phase_29_export_importable``).
"""

from __future__ import annotations

import importlib

import pytest


PHASE_29_NEW_EXPORTS = {
    "SuccessorHop",
    "discover_for_capacity",
    "discover_for_datastate",
    "rediscover_all",
    "DiscoveryFailedError",
}


PHASE_30_LIFTED_EXPORTS = {
    "invoke",
    "InvocationResult",
    "call_capacity",
    "Pipeline",
    "PipelineStep",
    "find_pipeline",
    "ProblemTraceRecord",
    "ProblemTraceSink",
    "emit_problem_trace",
    "PipelineNotFoundError",
    "ProblemTraceError",
}


def test_phase_29_exports_5_new_names():
    import mindsos_capacity
    all_set = set(mindsos_capacity.__all__)
    missing = PHASE_29_NEW_EXPORTS - all_set
    assert not missing, f"Phase 29 new exports missing from __all__: {missing}"


def test_phase_30_surface_exported_at_phase_30():
    """Sentinel flipped from Phase 29 R1 PB-20 / R4 probe 6.

    Originally asserted absence; Phase 30's ADR-0066 §Implementation
    + ADR-0072 §amendment-1 + ADR-0074 §Implementation footers lifted
    the invoke + Pipeline + ProblemTrace surface.
    """
    import mindsos_capacity
    all_set = set(mindsos_capacity.__all__)
    missing = PHASE_30_LIFTED_EXPORTS - all_set
    assert not missing, (
        f"Phase 30 lifted surface missing from __all__: {missing}"
    )


def test_phase_30_export_count_is_95():
    """Sentinel flipped from Phase 29 R5 PB-41 estimate.

    Originally asserted 82-86 range (Phase 29 baseline 84 ±2). Phase 30
    adds +11 exports → 95 total per `mindsos_capacity/__init__.py`
    Phase 30 §Excluded (defer) docstring + R2 PB-31(a) + R4 PB-50(a)
    locks.
    """
    import mindsos_capacity
    n = len(mindsos_capacity.__all__)
    assert n == 95, (
        f"Phase 30 __all__ count {n} != expected 95 "
        f"(Phase 29 baseline 84 + 11 new)"
    )


@pytest.mark.parametrize("name", sorted(PHASE_29_NEW_EXPORTS))
def test_phase_29_export_importable(name: str):
    """Each new export resolves to an actual symbol at runtime."""
    import mindsos_capacity
    assert hasattr(mindsos_capacity, name), (
        f"Phase 29 export {name!r} listed in __all__ but missing at runtime"
    )
