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


def test_phase_40_export_count_is_114():
    """Sentinel-flip ledger: 95 (P30) -> 97 (P31) -> 110 (P33) -> 114 (P40).

    Phase 40 X1 lifts +4 over Phase 33 (FamilyDontKnowShape, FAMILY_RULES,
    family_rule_for, DS_UNHANDLED_INPUT per ADR-0157). REALM_* + RESERVED_REALMS
    are imported directly from mindsos_capacity.identifiers by consumers and
    are not surfaced in the package __all__.
    """
    import mindsos_capacity
    n = len(mindsos_capacity.__all__)
    assert n == 114, (
        f"Phase 40 __all__ count {n} != expected 114 "
        f"(Phase 33 baseline 110 + 4 new at Phase 40)"
    )


PHASE_40_NEW_EXPORTS = {
    "FamilyDontKnowShape",
    "FAMILY_RULES",
    "family_rule_for",
    "DS_UNHANDLED_INPUT",
}


def test_phase_40_new_exports_present():
    import mindsos_capacity
    all_set = set(mindsos_capacity.__all__)
    missing = PHASE_40_NEW_EXPORTS - all_set
    assert not missing, f"Phase 40 new exports missing from __all__: {missing}"


@pytest.mark.parametrize("name", sorted(PHASE_40_NEW_EXPORTS))
def test_phase_40_export_importable(name: str):
    import mindsos_capacity
    assert hasattr(mindsos_capacity, name), (
        f"Phase 40 export {name!r} listed in __all__ but missing at runtime"
    )


@pytest.mark.parametrize("name", sorted(PHASE_29_NEW_EXPORTS))
def test_phase_29_export_importable(name: str):
    """Each new export resolves to an actual symbol at runtime."""
    import mindsos_capacity
    assert hasattr(mindsos_capacity, name), (
        f"Phase 29 export {name!r} listed in __all__ but missing at runtime"
    )
