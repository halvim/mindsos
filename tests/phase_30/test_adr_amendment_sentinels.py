"""Phase 30 ADR amendment sentinels.

Per Phase 30 R3 PB-38(a) + R5 PB-55 + R5 PB-62: 4 ADR touches in the
parent ADR tree (`/Layered Intelligence/docs/decisions/adr/` per
Model C — parent has no .git; ADRs live there). ADR-0072 gets BOTH
§amendment-1 AND §Implementation; the others get §Implementation
footers.

These sentinels skip in-container when the parent tree is not COPYed
into the test image (Model C pattern; same as Phase 28+29's
`test_adr_amendment_sentinels.py` skip-when-absent behaviour).
"""

from __future__ import annotations

from pathlib import Path

import pytest


_PARENT_ADR_DIR = Path("/Layered Intelligence/docs/decisions/adr")


_AMENDMENTS = [
    (
        "0066-capacity-iri-form.md",
        "§Implementation (2026-05-25, Phase 30 — InvocationResult + call_capacity export lift)",
    ),
    (
        "0071-pipeline-finder-bfs.md",
        "§Implementation (2026-05-25, Phase 30)",
    ),
    (
        "0072-invoke-never-raises.md",
        "§amendment-1 (2026-05-25, Phase 30 — InvocationResult field rename)",
    ),
    (
        "0072-invoke-never-raises.md",
        "§Implementation (2026-05-25, Phase 30)",
    ),
    (
        "0074-problem-trace-anomaly-only.md",
        "§Implementation (2026-05-25, Phase 30)",
    ),
]


@pytest.mark.parametrize("filename,marker", _AMENDMENTS)
def test_phase_30_adr_footer_present(filename: str, marker: str):
    """Each Phase 30 ADR footer/amendment is present in the parent file."""
    path = _PARENT_ADR_DIR / filename
    if not path.exists():
        pytest.skip(
            f"ADR file {path} not COPYed into test image (Model C "
            f"sentinel; verified out-of-container)"
        )
    content = path.read_text()
    assert marker in content, (
        f"Phase 30 footer not found in {filename}; "
        f"expected marker: {marker!r}"
    )
