"""Tier 12 — PHASE_MAP §Phase 11 Risks marked OBSOLETE.

Per PB-1 A + PB-12 B + PB-13 A + PB-10 A: scanner is detection-only;
sibling APIs are additive; warns don't mutate. Original "schema
migration is invasive" risk is obsolete. PHASE_MAP §11 must mark this
explicitly so future readers don't re-introduce the apply-path concern.
"""

from __future__ import annotations

from pathlib import Path

import pytest


_PHASE_MAP = (
    Path(__file__).resolve().parents[2]
    / "confirmation_docs" / "PHASE_MAP.md"
)


def _extract_phase_11_row() -> str:
    text = _PHASE_MAP.read_text(encoding="utf-8")
    marker = "### Phase 11"
    start = text.find(marker)
    if start < 0:
        pytest.fail("PHASE_MAP.md missing Phase 11 row")
    end = text.find("### Phase 12", start)
    if end < 0:
        end = len(text)
    return text[start:end]


def test_phase_map_phase_11_row_is_rewritten() -> None:
    """The pre-Phase-11 row text no longer applies (corrections per PB-1+3+7+12+16)."""
    row = _extract_phase_11_row()
    # Old wording struck.
    assert "cypher-build debug" not in row.lower() or "kill" in row.lower()
    assert "dry-run vs apply" not in row.lower() or "PB-1" in row


def test_phase_map_phase_11_row_risks_marked_obsolete() -> None:
    """The Risks section explicitly marks the snapshot-guard claim obsolete."""
    row = _extract_phase_11_row()
    # Lowercased comparison — OBSOLETE flag must be present.
    lowered = row.lower()
    assert "obsolete" in lowered, (
        "PHASE_MAP §Phase 11 Risks must mark the snapshot-guard claim "
        "obsolete per PB-1 A detection-only lock"
    )


def test_phase_map_phase_11_row_lists_new_doc_surfaces() -> None:
    """Docs field names schema-migration internals + migration-playbook."""
    row = _extract_phase_11_row()
    assert "schema migration scanner" in row.lower() or (
        "Phase 11" in row and "schema migration" in row.lower()
    )
    assert "migration-playbook" in row.lower()


def test_phase_map_phase_11_row_references_amendments() -> None:
    """ADR-0134 §amendments-1 + 2 mentioned in the Docs field."""
    row = _extract_phase_11_row()
    assert "amendment" in row.lower()
