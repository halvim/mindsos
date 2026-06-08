"""Phase 45 sentinel — ADR-0162 (L3 dream family) landing checks.

Rail D chain root (link from Phase 38; PHASE_MAP Phase 45 row). Rail D is
a fresh single-phase rail, so this mirrors the Phase 44 (Rail C)
independent-rail sentinel: no chain-parent file assertion; the ADR is read
by full filename; Accepted + §Implementation (Phase 45) footer are
anchored.
"""

from __future__ import annotations

from pathlib import Path

_ADR_DIR = Path(__file__).parents[2] / "docs" / "decisions" / "adr"


def _read(name: str) -> str:
    return (_ADR_DIR / name).read_text(encoding="utf-8")


def test_adr_0162_present_and_accepted():
    body = _read("0162-l3-dream-family.md")
    assert "status: Accepted" in body
    assert "**Status:** Accepted" in body


def test_adr_0162_implementation_footer_phase_45():
    body = _read("0162-l3-dream-family.md")
    assert "§Implementation (Phase 45" in body


def test_adr_0162_names_three_capacities_and_policies():
    body = _read("0162-l3-dream-family.md")
    for token in (
        "dream.maintenance",
        "dream.exploration",
        "dream.retry",
        "replay_recorded",
        "re_execute_capacities",
        "replan-injection",
        "OPTIONAL_RETURN",
    ):
        assert token in body, f"{token!r} missing from ADR-0162 body"
