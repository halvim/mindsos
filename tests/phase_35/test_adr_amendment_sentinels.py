"""Phase 35 — ADR-0147 §amendment-1 sentinels + PHASE_MAP / tracker anchors.

Mirrors the Phase 14a → 15a → 15b → **35** sentinel-chain pattern: ADRs
live in the parent project tree
(``/Layered Intelligence/docs/decisions/adr/``) per Model C
(`feedback_docs_source_of_truth.md`), NOT under ``halvim_mindsos/``, and
are NOT COPYd into the runtime container image. The ADR-anchored
sentinels here run in the sandbox where the parent tree IS reachable
but **skip in container** when the parent path is unreachable. The
non-ADR sentinels (PHASE_MAP + tracker) live under halvim_mindsos/ and
run everywhere.

Phase 35 is design-only (PHASE_MAP §1 exception); this file is the only
test surface shipped in this phase. The sentinel chain
14a → 15a → 15b → 35 protects the ADR amendments against silent
removal/edit since the parent tree is not git-tracked (Model C).
"""

from __future__ import annotations

from pathlib import Path

import pytest


# Parent-project ADR dir: halvim_mindsos/tests/phase_35/ →
# halvim_mindsos/tests/ → halvim_mindsos/ → /Layered Intelligence/.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT / "docs" / "decisions" / "adr"


def _skip_if_adr_dir_missing() -> None:
    if not _ADR_DIR.exists():
        pytest.skip(
            f"ADR directory {_ADR_DIR!r} unreachable (in-container run); "
            f"ADRs live in parent project tree per Model C."
        )


# ── ADR-0147 sentinels (parent-tree; skip in container) ─────────────────


def test_adr_0147_status_accepted() -> None:
    """ADR-0147 Status frontmatter must read `status: Accepted` post-Phase 35."""
    _skip_if_adr_dir_missing()
    adr = _ADR_DIR / "0147-l3-per-flow-write-capacity-build-pattern.md"
    assert adr.exists(), f"ADR-0147 file missing: {adr}"
    content = adr.read_text(encoding="utf-8")
    # Frontmatter line — must be exactly `status: Accepted` in YAML block.
    assert "status: Accepted" in content, (
        "ADR-0147 Status frontmatter not flipped to Accepted — "
        "see Phase 35 design log §3 + ADR-0147 §amendment-1 for the flip."
    )


def test_adr_0147_amendment_1_present() -> None:
    """ADR-0147 §amendment-1 — Status flip + 3 clauses (per-flow gate closure).

    Anchors per Phase 35 R4 PB-E4 lock: amendment header, contract-surface
    reframing of criterion (a), anticipatory carve-out, strict-forward rule.
    """
    _skip_if_adr_dir_missing()
    adr = _ADR_DIR / "0147-l3-per-flow-write-capacity-build-pattern.md"
    assert adr.exists(), f"ADR-0147 file missing: {adr}"
    content = adr.read_text(encoding="utf-8")
    # Amendment header — Phase 35 ship marker.
    assert "amendment-1 (Phase 35 ship" in content, (
        "ADR-0147 §amendment-1 (Phase 35) header missing — "
        "see Phase 35 design log §3 + R4 PB-A4."
    )
    # Clause 1 — criterion (a) reframed via contract-surface evidence.
    assert "shipped through the" in content, (
        "ADR-0147 §amendment-1 clause 1 wording missing — see R2 PB-β."
    )
    assert "KLWriteHandle" in content
    assert "contract surface" in content
    # Clause 2 — anticipatory carve-out.
    assert "anticipatory" in content, (
        "ADR-0147 §amendment-1 clause 2 'anticipatory' marker missing — "
        "see R3 PB-A3 clause 2."
    )
    # Clause 3 — per-flow strict going forward.
    assert "per-flow" in content
    assert "strict" in content, (
        "ADR-0147 §amendment-1 clause 3 'strict' forward-rule marker missing "
        "— see R3 PB-A3 clause 3."
    )


def test_adr_0147_implementation_phase_35_footer_present() -> None:
    """ADR-0147 §Implementation (Phase 35) footer — Status-flip event."""
    _skip_if_adr_dir_missing()
    adr = _ADR_DIR / "0147-l3-per-flow-write-capacity-build-pattern.md"
    assert adr.exists(), f"ADR-0147 file missing: {adr}"
    content = adr.read_text(encoding="utf-8")
    assert "§Implementation (Phase 35" in content, (
        "ADR-0147 §Implementation Phase 35 footer missing — "
        "see Phase 35 design log §3 + R4 PB-B4."
    )
    assert "design-only" in content


# ── halvim-tree sentinels (run everywhere) ─────────────────────────────


def test_phase_map_section_35_inline_amendment() -> None:
    """PHASE_MAP §Phase 35 carries §inline-amendment block post-Phase 35 ship.

    Mirrors Phase 34's §inline-amendment pattern (PHASE_MAP §34) — Phase 35
    documents the wording-vs-reality gap in the §35 features line by adding
    an inline-amendment block under the row (not a strikethrough). See R3
    PB-G + R2 PB-ζ for the locked text shape.
    """
    phase_map = _REPO_ROOT / "confirmation_docs" / "PHASE_MAP.md"
    assert phase_map.exists(), f"PHASE_MAP.md missing: {phase_map}"
    content = phase_map.read_text(encoding="utf-8")
    # Amendment block marker (R2 PB-ζ locked wording).
    assert "Phase 35 ship; R0 PB-1 scope-shape resolution" in content, (
        "PHASE_MAP §35 §inline-amendment block missing — see Phase 35 "
        "design log §3 + R2 PB-ζ."
    )
    # Cross-references to the load-bearing decisions made at Phase 35.
    assert "ADR-0147 §amendment-1" in content
    assert "Phase 14a + Phase 15b precedent" in content, (
        "PHASE_MAP §35 amendment must cite design-only precedent — see "
        "R2 PB-α."
    )


def test_tracker_last_confirmed_phase_is_35() -> None:
    """L3-capacity-write-flows.md `last_confirmed_phase` bumped 34 → 35.

    The tracker is the canonical full-list source per ADR-0147 §Consequences
    mitigation. Phase 35 bumps its `last_confirmed_phase` front-matter to
    35 and adds a Provenance note cross-referencing §amendment-1 clause 2
    for the anticipatory carve-out (R3 PB-G3).
    """
    tracker = (
        _REPO_ROOT
        / "docs"
        / "dev"
        / "coordinated-changes"
        / "L3-capacity-write-flows.md"
    )
    assert tracker.exists(), f"tracker page missing: {tracker}"
    content = tracker.read_text(encoding="utf-8")
    assert "last_confirmed_phase: 35" in content, (
        "tracker `last_confirmed_phase` not bumped to 35 — see R3 PB-G3."
    )
    # Provenance-note marker for the anticipatory carve-out cross-ref.
    assert "Provenance note" in content, (
        "tracker Provenance note for anticipatory carve-out missing — "
        "see R3 PB-G3."
    )
    assert "anticipatory" in content
    assert "ADR-0147 §amendment-1" in content
