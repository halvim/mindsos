"""Phase 15b — ADR-0134 §amendment-3 + ADR-0150 §amendment-2 sentinels.

Mirrors Phase 13/14/14a/15a sentinel pattern: ADRs live in the parent
project tree (``/Layered Intelligence/docs/decisions/adr/``) per Model
C (`feedback_docs_source_of_truth.md`), NOT under ``halvim_mindsos/``,
and are NOT COPYd into the runtime container image. These sentinels
run in the sandbox where the parent tree IS reachable but **skip in
container** when the parent path is unreachable.

Phase 15b is design-only (PHASE_MAP §1 exception); this file is the
only test surface shipped in this phase. The sentinel chain
14a → 15a → 15b protects the ADR amendments against silent
removal/edit since the parent tree is not git-tracked (Model C).
"""

from __future__ import annotations

from pathlib import Path

import pytest


# Parent-project ADR dir: halvim_mindsos/tests/phase_15b/ →
# halvim_mindsos/tests/ → halvim_mindsos/ → /Layered Intelligence/.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT / "docs" / "decisions" / "adr"


def _skip_if_adr_dir_missing() -> None:
    if not _ADR_DIR.exists():
        pytest.skip(
            f"ADR directory {_ADR_DIR!r} unreachable (in-container run); "
            f"ADRs live in parent project tree per Model C."
        )


def test_adr_0134_amendment_3_present() -> None:
    """ADR-0134 §amendment-3 — documentary alignment + §closing relaxation + Status flip."""
    _skip_if_adr_dir_missing()
    adr = _ADR_DIR / "0134-schema-migration-scanner.md"
    assert adr.exists(), f"ADR-0134 file missing: {adr}"
    content = adr.read_text(encoding="utf-8")
    assert "amendment-3 (Phase 15b ship" in content, (
        "ADR-0134 §amendment-3 (Phase 15b) header missing — "
        "see Phase 15b design log §3 + Round 3.5 PB-14 + Round 4 PB-16."
    )
    # §3a documentary anchors — Phase 11's shipped API surface.
    assert "amendment-3, §3a" in content
    assert "removed_hyperedge_type" in content  # 5th ViolationKind
    assert "old_schema_name" in content
    assert "DetailMode" in content
    # §3b §closing relaxation + Status flip.
    assert "amendment-3, §3b" in content
    assert "ADR moves from Proposed to Accepted when" in content


def test_adr_0134_status_accepted() -> None:
    """ADR-0134 Status frontmatter must read `status: Accepted` post-Phase 15b."""
    _skip_if_adr_dir_missing()
    adr = _ADR_DIR / "0134-schema-migration-scanner.md"
    assert adr.exists(), f"ADR-0134 file missing: {adr}"
    content = adr.read_text(encoding="utf-8")
    # Frontmatter line — must be exactly `status: Accepted` in YAML block.
    assert "status: Accepted" in content, (
        "ADR-0134 Status frontmatter not flipped to Accepted — "
        "see Phase 15b ADR-0134 §amendment-3 §3b for the flip."
    )


def test_adr_0150_amendment_2_present() -> None:
    """ADR-0150 §amendment-2 — supporting-evidence correction; architectural decision unchanged."""
    _skip_if_adr_dir_missing()
    adr = _ADR_DIR / "0150-l2-knowledge-lifecycle.md"
    assert adr.exists(), f"ADR-0150 file missing: {adr}"
    content = adr.read_text(encoding="utf-8")
    assert "amendment-2 (Phase 15b ship" in content, (
        "ADR-0150 §amendment-2 (Phase 15b) header missing — "
        "see Phase 15b design log §3 + Round 5 PB-19."
    )
    # Supporting-evidence correction anchors.
    assert "supporting-evidence correction" in content
    assert "PHASE_MAP §Phase 28" in content  # closure phase TBD reference
    # Architectural decision unchanged.
    assert "Global-only at v1" in content
