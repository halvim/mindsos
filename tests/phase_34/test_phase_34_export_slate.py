"""Phase 34 — __init__.py export slate stability.

Phase 34 adds ZERO new top-level exports. ``InvocationResult.write_outcome``
is a dataclass field (not a top-level export). ``_IRI_BUILDERS`` is
private. ``write_and_validate`` is a method, not a module export.
Count stays at 110 (R4 §am-impl-7 forward-anchor sentinel).
"""

from __future__ import annotations

import mindsos_capacity
import mindsos_knowledge


def test_phase_34_export_count_stable_at_110():
    """Forward-anchor sentinel: Phase 34 adds no new exports."""
    n = len(mindsos_capacity.__all__)
    assert n == 110, (
        f"Phase 34 __all__ count {n} != 110 (no new exports expected; "
        "if you added one, bump this and add to R4 §am-impl-7 audit)."
    )


def test_phase_34_version_bumped():
    """Phase 39 ship: subsequent phases advance this assertion to the
    current phase per the manifest-bump pattern."""
    assert mindsos_capacity.__version__ == "0.0.0+phase39"
    assert mindsos_knowledge.__version__ == "0.0.0+phase39"


def test_phase_33_exports_remain_intact():
    """No Phase 33 export was dropped at Phase 34."""
    phase_33_set = {
        "WriteResult",
        "WriteOutcome",
        "WriteHandleNotWiredError",
        "CapabilityDeniedError",
        "CATEGORY_CONSOLIDATE",
        "DS_MM_COMPOSITE_INSTANCE",
        "mm_composite_datastates",
        "build_consolidate_mm",
        "install_consolidate_capacities",
        "DS_PROBLEM_TRACE_RECORD",
        "problem_trace_datastates",
        "build_trace_problem",
        "install_trace_capacities",
    }
    missing = phase_33_set - set(mindsos_capacity.__all__)
    assert not missing, f"Phase 33 exports dropped at Phase 34: {sorted(missing)}"


def test_kl_write_handle_still_exported_from_mindsos_knowledge():
    """ADR-0143 Accepted at Phase 34; handle still re-exported."""
    assert "KLWriteHandle" in mindsos_knowledge.__all__
    assert hasattr(mindsos_knowledge, "KLWriteHandle")
