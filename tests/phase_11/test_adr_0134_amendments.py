"""Tier 10 — ADR-0134 §Revisions amendments-1 + 2 sentinel.

Asserts the two Phase 11 amendments landed in the canonical ADR file
at `/Layered Intelligence/docs/decisions/adr/0134-schema-migration-scanner.md`.
ADRs are immutable post-Accepted; ADR-0134 is still Proposed so
amendments here are allowed per `feedback_docs_source_of_truth.md`.
"""

from __future__ import annotations

from pathlib import Path

import pytest


_ADR_CANDIDATES = [
    # Sandbox + Mac paths converge on this relative path from repo root
    # (run by pytest from `halvim_mindsos/`).
    Path(__file__).resolve().parents[2].parent
        / "docs" / "decisions" / "adr"
        / "0134-schema-migration-scanner.md",
    # Fallback when invoked with cwd inside `halvim_mindsos/`.
    Path("../docs/decisions/adr/0134-schema-migration-scanner.md"),
]


def _read_adr() -> str:
    for candidate in _ADR_CANDIDATES:
        try:
            return candidate.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
    pytest.skip(
        f"ADR-0134 not reachable from any candidate path "
        f"({[str(p) for p in _ADR_CANDIDATES]}); skipping sentinel."
    )


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


def test_adr_0134_stays_proposed() -> None:
    """ADR-0134 status remains Proposed per PB-5 A lock."""
    text = _read_adr()
    # status line in frontmatter.
    assert "status: Proposed" in text
