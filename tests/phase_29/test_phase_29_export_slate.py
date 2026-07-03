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


# Phase 42 (ADR-0156): the Phase 29 TYPE_COMPAT/discovery exports were
# RETIRED. This file (the surviving Phase 29 slate sentinel) flips its
# original "present" checks to retirement checks, mirroring the Phase 41
# phase_31 resident-retirement pattern.
PHASE_29_RETIRED_EXPORTS = {
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
    # composition-lifecycle (ADR-0071 §am-2): the linear Pipeline/PipelineStep
    # were replaced by the Pipeline result type + DAGStep/DAGEdge.
    "Pipeline",
    "DAGStep",
    "DAGEdge",
    "find_pipeline",
    "ProblemTraceRecord",
    "ProblemTraceSink",
    "emit_problem_trace",
    "PipelineNotFoundError",
    "ProblemTraceError",
}


def test_phase_29_discovery_exports_retired():
    # ADR-0156 (Phase 42): TYPE_COMPAT/discovery surface retired.
    import mindsos_capacity
    present = PHASE_29_RETIRED_EXPORTS & set(mindsos_capacity.__all__)
    assert not present, f"Phase 29 exports should be retired but still in __all__: {present}"


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


def test_export_count_is_139():
    """Sentinel-flip ledger: 95 (P30) -> 97 (P31) -> 110 (P33) -> 114 (P40)
    -> 112 (P41) -> 117 (P42) -> 118 (P45) -> 128 (F9) -> 139
    (composition-lifecycle).

    composition-lifecycle (ADR-0071 §am-2 + ADR-0159 §am-1) net +11:
    -2 (retire ``Pipeline``/``PipelineStep``) +7 finder seam / DAG type
    (``Pipeline``, ``DAGStep``, ``DAGEdge``, ``START``, ``Finder``,
    ``BFSFinder``, ``ConjunctionFinder``) +2 composite-persistence
    (``COMPOSITE_DAG``, ``composite_dependencies``) +4 typed input-group
    (``INPUT_GROUP_ALL_REQUIRED``, ``INPUT_GROUP_ANY_OF``,
    ``INPUT_GROUP_FOLD``, ``INPUT_GROUPS``).
    """
    import mindsos_capacity
    n = len(mindsos_capacity.__all__)
    assert n == 139, (
        f"__all__ count {n} != expected 139 "
        f"(F9 baseline 128 + 11 composition-lifecycle net)"
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


@pytest.mark.parametrize("name", sorted(PHASE_29_RETIRED_EXPORTS))
def test_phase_29_export_retired_and_unresolvable(name: str):
    """Each retired export is absent from __all__ AND unresolvable (ADR-0156)."""
    import mindsos_capacity
    assert name not in mindsos_capacity.__all__, (
        f"Retired Phase 29 export {name!r} still listed in __all__"
    )
    assert not hasattr(mindsos_capacity, name), (
        f"Retired Phase 29 export {name!r} still resolvable at runtime"
    )
