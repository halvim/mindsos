"""Phase 28 — InvocationResult / call_capacity NOT exported (R3 PB-38 sentinel)."""

from __future__ import annotations

import pytest


def test_invocation_result_and_call_capacity_not_in_all():
    import mindsos_capacity

    assert "InvocationResult" not in mindsos_capacity.__all__, (
        "InvocationResult must not be exported from mindsos_capacity until "
        "Phase 30 lifts the runtime.py surface. See Phase 27 R3 PB-26."
    )
    assert "call_capacity" not in mindsos_capacity.__all__, (
        "call_capacity must not be exported from mindsos_capacity until "
        "Phase 30. See Phase 27 R3 PB-26."
    )


def test_invocation_result_and_call_capacity_not_top_level_importable():
    with pytest.raises(ImportError):
        from mindsos_capacity import InvocationResult
    with pytest.raises(ImportError):
        from mindsos_capacity import call_capacity
