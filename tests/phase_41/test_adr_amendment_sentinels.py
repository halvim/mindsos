"""Phase 41 ADR sentinel chain (link from Phase 40).

Anchors the ratified text of ADR-0155 (monitor lifecycle relocated from
L3 to L4 substrate). ADR-0155 is ``status: Accepted`` on disk from the
L1/L3 reframe chat (2026-06-01); Phase 41 implements it + pins canonical
strings + appends the Phase-41 §Implementation marker. Also verifies the
superseded ADR-0073 status flip (PB-6).

Mirrors the Phase 40 sentinel pattern (host-filesystem assert-exists).
"""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT / "docs" / "decisions" / "adr"

assert _ADR_DIR.exists(), f"ADR directory missing at expected path: {_ADR_DIR}."


def _read_adr(slug: str) -> str:
    adr = _ADR_DIR / slug
    assert adr.exists(), f"ADR file missing: {adr}"
    return adr.read_text(encoding="utf-8")


_ADR_0155 = "0155-monitor-lifecycle-relocated-from-l3-to-l4.md"
_ADR_0073 = "0073-residents-descriptive.md"


def test_adr_0155_accepted():
    assert "status: Accepted" in _read_adr(_ADR_0155)


def test_adr_0155_supersedes_0073():
    assert "supersedes: [ADR-0073]" in _read_adr(_ADR_0155)


def test_adr_0155_retire_keep_surface():
    text = _read_adr(_ADR_0155)
    assert "iter_monitors" in text
    assert "KIND_MONITOR" in text
    assert "MonitorSubscriptionRegistry" in text


def test_adr_0155_phase_41_implementation_marker():
    assert "§Implementation (2026-06-05, Phase 41)" in _read_adr(_ADR_0155)


def test_adr_0073_flipped_to_superseded():
    assert "status: Superseded" in _read_adr(_ADR_0073)
