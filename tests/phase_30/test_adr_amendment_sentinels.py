"""Phase 30 ADR amendment sentinels.

**Current behaviour (2026-09-16):** ``docs/`` is in this repo and is copied into
the test image, so a missing ADR is a FAILURE here, never a skip. The Model C
layout described below is historical;
``tests/architecture/test_no_skip_when_docs_missing.py`` keeps it that way.

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


_PARENT_ADR_DIR = Path(__file__).resolve().parents[2] / "docs" / "decisions" / "adr"


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
        pytest.fail(
            f"ADR file {path} is missing; docs/ is in the repo and copied "
            f"into the test image, so this is a real failure."
        )
    content = path.read_text()
    assert marker in content, (
        f"Phase 30 footer not found in {filename}; "
        f"expected marker: {marker!r}"
    )
