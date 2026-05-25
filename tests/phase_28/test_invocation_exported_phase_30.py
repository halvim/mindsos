"""Phase 28 sentinel FLIPPED at Phase 30 (R0 PB-9(a) + R3 PB-37(a) + R4 PB-45(a)).

Original Phase 28 R3 PB-38 sentinel (`test_invocation_not_exported.py`)
asserted ``InvocationResult`` and ``call_capacity`` were NOT exported
from ``mindsos_capacity``. Phase 30 lifts those exports per ADR-0066
§Implementation (Phase 30 footer) + ADR-0072 §amendment-1.

This file replaces ``test_invocation_not_exported.py`` (R3 PB-37(a)
file rename — whole file is the sentinel). The flip is bidirectional
evidence: previously raised ImportError, now imports succeed.

See `[[feedback-parity-test-sentinel-flip-at-target-phase]]`.
"""

from __future__ import annotations


def test_invocation_result_and_call_capacity_in_all_at_phase_30():
    import mindsos_capacity

    assert "InvocationResult" in mindsos_capacity.__all__, (
        "InvocationResult must be exported from mindsos_capacity at "
        "Phase 30 per ADR-0066 §Implementation (Phase 30) export-lift "
        "footer. Sentinel previously asserted absence at Phase 27/28/29."
    )
    assert "call_capacity" in mindsos_capacity.__all__, (
        "call_capacity must be exported from mindsos_capacity at "
        "Phase 30 per ADR-0066 §Implementation (Phase 30) export-lift "
        "footer. Sentinel previously asserted absence at Phase 27/28/29."
    )


def test_invocation_result_and_call_capacity_top_level_importable_at_phase_30():
    # These imports MUST succeed at Phase 30 (sentinel flip).
    from mindsos_capacity import InvocationResult, call_capacity

    assert InvocationResult is not None
    assert callable(call_capacity)
