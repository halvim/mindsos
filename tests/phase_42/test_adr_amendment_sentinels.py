"""Phase 42 — ADR amendment sentinel chain (ADR-0156 + ADR-0159 + 8 amends).

Chains from the Phase 41 sentinel (tests/phase_41/test_adr_amendment_sentinels.py),
which chained from Phase 40, rooted at Phase 39. Anchors:
  - ADR-0156 + ADR-0159 Accepted + their Phase-42 §Implementation footers.
  - ADR-0069 + ADR-0086 flipped to Superseded by ADR-0156.
  - The 8 amended ADRs (0070/0071/0132 per ADR-0156; 0072/0078/0143/0146/0147
    per ADR-0159) each carrying a Phase-42 §Amendment paragraph.
"""

from __future__ import annotations

import pathlib

import pytest

_ADR = pathlib.Path(__file__).resolve().parents[2] / "docs" / "decisions" / "adr"
_PHASE_41_SENTINEL = (
    pathlib.Path(__file__).resolve().parents[1]
    / "phase_41"
    / "test_adr_amendment_sentinels.py"
)


def _read(stem: str) -> str:
    matches = list(_ADR.glob(f"{stem}-*.md"))
    assert matches, f"ADR {stem} not found"
    return matches[0].read_text(encoding="utf-8")


def test_chain_links_from_phase_41():
    assert _PHASE_41_SENTINEL.is_file(), "Phase 41 sentinel (chain parent) missing"


def test_adr_0156_accepted_and_implemented():
    text = _read("0156")
    assert "status: Accepted" in text
    assert "§Implementation (Phase 42" in text


def test_adr_0159_accepted_and_implemented():
    text = _read("0159")
    assert "status: Accepted" in text
    assert "§Implementation (Phase 42" in text


def test_adr_0069_and_0086_superseded_by_0156():
    for stem in ("0069", "0086"):
        text = _read(stem)
        assert "status: Superseded" in text, f"{stem} not flipped to Superseded"
        assert "ADR-0156" in text, f"{stem} missing superseded_by ADR-0156"


@pytest.mark.parametrize("stem", ["0070", "0071", "0132"])
def test_adr_0156_amendment_paragraphs(stem):
    assert "§Amendment (Phase 42" in _read(stem)
    assert "ADR-0156" in _read(stem)


@pytest.mark.parametrize("stem", ["0072", "0078", "0143", "0146", "0147"])
def test_adr_0159_amendment_paragraphs(stem):
    assert "§Amendment (Phase 42" in _read(stem)
    assert "ADR-0159" in _read(stem)
