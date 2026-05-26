"""Phase 29 — __init__.py export slate.

Sentinel-flip ledger (per ``[[feedback-parity-test-sentinel-flip-at-target-phase]]``):

- Phase 30 (B-30-T1): ``test_phase_29_does_not_export_phase_30_surface``
  inverted to "present-at-Phase-30"; ``test_phase_29_export_count_around_84``
  widened to count == 95.
- Phase 31 (B-31-T2): count sentinel re-flipped to 97
  (ResidentSubscription + ResidentError lift).

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


def test_phase_31_export_count_is_97():
    """B-31-T2 sentinel-flip in place — Phase 31 lifts +2 over Phase 30.

    Originally asserted 95 at Phase 30 (Phase 29 baseline 84 + 11 new).
    Phase 31 adds ResidentSubscription + ResidentError → 97. Same class
    as B-31-T0 + B-30-T1 — `tests/phase_(N-1)/test_phase_*_export_slate.py`
    is a sentinel-flip target at each subsequent phase ship.
    """
    import mindsos_capacity
    n = len(mindsos_capacity.__all__)
    assert n == 97, (
        f"Phase 31 __all__ count {n} != expected 97 "
        f"(Phase 30 baseline 95 + 2 new at Phase 31)"
    )


@pytest.mark.parametrize("name", sorted(PHASE_29_NEW_EXPORTS))
def test_phase_29_export_importable(name: str):
    """Each new export resolves to an actual symbol at runtime."""
    import mindsos_capacity
    assert hasattr(mindsos_capacity, name), (
        f"Phase 29 export {name!r} listed in __all__ but missing at runtime"
    )
