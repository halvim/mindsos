"""Tier 10 — ADR-0134 §Revisions amendments-1 + 2 sentinel.

Asserts the two Phase 11 amendments are present in
``docs/decisions/adr/0134-schema-migration-scanner.md``.

**Current behaviour (2026-09-16):** until this date the file looked for the
ADR one level ABOVE the repo root (the old "Model C" parent tree), so all four
tests skipped on every run. The path is now the repo's own ``docs/`` (copied
into the test image) and a missing ADR fails. The fourth test,
``test_adr_0134_stays_proposed``, was deleted rather than revived: ADR-0134 was
accepted at Phase 15b (§amendment-3), which
``tests/phase_15b/test_adr_amendment_sentinels.py::test_adr_0134_status_accepted``
already asserts.
"""

from __future__ import annotations

from pathlib import Path

import pytest


_ADR_0134 = (
    Path(__file__).resolve().parents[2]
    / "docs" / "decisions" / "adr" / "0134-schema-migration-scanner.md"
)


def _read_adr() -> str:
    if not _ADR_0134.is_file():
        pytest.fail(f"ADR-0134 is missing: {_ADR_0134}")
    return _ADR_0134.read_text(encoding="utf-8")


def test_adr_0134_has_revisions_section() -> None:
    """ADR-0134 carries the new ``## Revisions`` section."""
    text = _read_adr()
    assert "## Revisions" in text


def test_adr_0134_amendment_1_per_distinct_type_warn() -> None:
    """Amendment-1 documents per-distinct-type WARN granularity (PB-10 A)."""
    text = _read_adr()
    assert "amendment-1" in text
    assert "per-distinct-type" in text or "per distinct" in text
    assert "WARN" in text or "warn" in text


def test_adr_0134_amendment_2_policy_on_loader_not_falkor_config() -> None:
    """Amendment-2 documents policy placement on loader, not FalkorConfig (PB-14 A)."""
    text = _read_adr()
    assert "amendment-2" in text
    assert "FalkorConfig" in text
    assert "loader" in text
    assert "MINDSOS_UNKNOWN_EDGE_POLICY" in text
