"""Phase 29 ADR amendment sentinels.

Per Phase 29 R0 PB-6 (c) + R5 PB-42: 3 ADR touches in the parent
ADR tree (`/Layered Intelligence/docs/decisions/adr/` per Model C —
parent has no .git; ADRs live there). These sentinels skip in-
container when the parent tree is not COPYed into the test image
(Model C pattern; same as Phase 28's `test_adr_amendment_sentinels.py`
skip-when-absent behaviour).
"""

from __future__ import annotations

from pathlib import Path

import pytest


_PARENT_ADR_DIR = Path(__file__).resolve().parents[2] / "docs" / "decisions" / "adr"


_AMENDMENTS = [
    (
        "0069-type-compat-auto-discovery.md",
        "§Implementation (Phase 29 — 2026-05-25)",
    ),
    (
        "0086-auto-discovery-with-admin-override.md",
        "§Implementation (Phase 29 — 2026-05-25)",
    ),
    (
        "0070-five-constraint-kinds.md",
        "§Implementation (Phase 28 — 2026-05-25, closure footer at Phase 29 — 2026-05-25)",
    ),
]


@pytest.mark.parametrize("filename,marker", _AMENDMENTS)
def test_phase_29_adr_footer_present(filename: str, marker: str):
    """Each Phase 29 ADR amendment footer is present in the parent file."""
    path = _PARENT_ADR_DIR / filename
    if not path.exists():
        pytest.skip(
            f"ADR file {path} not COPYed into test image (Model C "
            f"sentinel; verified out-of-container)"
        )
    content = path.read_text()
    assert marker in content, (
        f"Phase 29 §Implementation footer not found in {filename}; "
        f"expected marker: {marker!r}"
    )
