"""Phase 29 — __init__.py export slate + non-touch list.

Per R5 PB-41 lock: Phase 28 baseline 79 exports + Phase 29 adds 5 →
84 exports. R1 PB-20 + R4 probe 6: Phase 29 does NOT introduce any
Phase 30 surface (invoke / InvocationResult / call_capacity /
problem_trace).
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


PHASE_30_FORBIDDEN_EXPORTS = {
    "invoke",
    "InvocationResult",
    "call_capacity",
    "problem_trace",
    "start_resident",
    "stop_resident",
}


def test_phase_29_exports_5_new_names():
    import mindsos_capacity
    all_set = set(mindsos_capacity.__all__)
    missing = PHASE_29_NEW_EXPORTS - all_set
    assert not missing, f"Phase 29 new exports missing from __all__: {missing}"


def test_phase_29_does_not_export_phase_30_surface():
    import mindsos_capacity
    all_set = set(mindsos_capacity.__all__)
    leaked = PHASE_30_FORBIDDEN_EXPORTS & all_set
    assert not leaked, (
        f"Phase 30 surface leaked into Phase 29 __all__: {leaked}"
    )


def test_phase_29_export_count_around_84():
    import mindsos_capacity
    n = len(mindsos_capacity.__all__)
    # Allow ±2 slack for any incidental adds (R5 PB-41 estimate; final
    # value driven by what was actually appended in __init__.py).
    assert 82 <= n <= 86, (
        f"Phase 29 __all__ count {n} outside expected 82-86 range "
        f"(Phase 28 baseline 79 + 5 new ≈ 84)"
    )


@pytest.mark.parametrize("name", sorted(PHASE_29_NEW_EXPORTS))
def test_phase_29_export_importable(name: str):
    """Each new export resolves to an actual symbol at runtime."""
    import mindsos_capacity
    assert hasattr(mindsos_capacity, name), (
        f"Phase 29 export {name!r} listed in __all__ but missing at runtime"
    )
