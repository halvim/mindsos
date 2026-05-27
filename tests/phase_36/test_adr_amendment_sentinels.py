"""Phase 36 — ADR-0139 §amendment-1 + ADR-0143 §Impl Phase 36 footer
+ PHASE_MAP §36 §inline-amendment + knowledge.md + review-checklist
sentinels.

Extends the Phase 14a → 15a → 15b → 35 → **36** sentinel chain (R3
PB-B3 wording extended at Phase 36). ADRs + ``docs/dev/internals/
knowledge.md`` live in the parent project tree
(``/Layered Intelligence/``) per Model C
(``[[feedback-docs-source-of-truth]]``); these sentinels skip in
container when the parent path is unreachable. Halvim-tree sentinels
(PHASE_MAP + review-checklist) run everywhere.

7 anchors per R5-PB-B (5 parent-tree + 2 halvim-tree).
"""

from __future__ import annotations

from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT.parent / "docs" / "decisions" / "adr"
_INTERNALS_DIR = _REPO_ROOT.parent / "docs" / "dev" / "internals"


def _skip_if_parent_dir_missing(p: Path) -> None:
    if not p.exists():
        pytest.skip(
            f"parent project path {p!r} unreachable (in-container run); "
            f"parent tree per Model C."
        )


# ── ADR-0139 sentinels (parent-tree; skip in container) ────────────────


def test_adr_0139_status_accepted() -> None:
    """ADR-0139 Status frontmatter must read `status: Accepted` post-Phase 36."""
    _skip_if_parent_dir_missing(_ADR_DIR)
    adr = _ADR_DIR / "0139-hybrid-invariant-home.md"
    assert adr.exists(), f"ADR-0139 file missing: {adr}"
    content = adr.read_text(encoding="utf-8")
    assert "status: Accepted" in content, (
        "ADR-0139 Status frontmatter not flipped to Accepted — "
        "see Phase 36 notes §3 + ADR-0139 §amendment-1 for the flip."
    )


def test_adr_0139_amendment_1_present() -> None:
    """ADR-0139 §amendment-1 — Status flip; per-flow extension for
    adapters; clarification (not relaxation) of §Accept(a).

    Anchors per R5-PB-B: amendment header, contract-surface evidence
    closure of (a), per-flow clause for adapter extension.
    """
    _skip_if_parent_dir_missing(_ADR_DIR)
    adr = _ADR_DIR / "0139-hybrid-invariant-home.md"
    content = adr.read_text(encoding="utf-8")
    assert "amendment-1 (Phase 36 ship" in content, (
        "ADR-0139 §amendment-1 (Phase 36) header missing — see Phase 36 "
        "notes §4 + R2-PB-E."
    )
    assert "validate_role_routing" in content, (
        "ADR-0139 §amendment-1 must cite the Phase-36-wired validator "
        "(role-routing) per §Accept(b) closure."
    )
    assert "per-flow" in content, (
        "ADR-0139 §amendment-1 clause 3 carry-forward (per-flow adapter "
        "extension) marker missing."
    )


def test_adr_0139_implementation_phase_36_footer_present() -> None:
    """ADR-0139 §Implementation (Phase 36) footer — Status-flip event."""
    _skip_if_parent_dir_missing(_ADR_DIR)
    adr = _ADR_DIR / "0139-hybrid-invariant-home.md"
    content = adr.read_text(encoding="utf-8")
    assert "§Implementation (Phase 36" in content, (
        "ADR-0139 §Implementation Phase 36 footer missing — see Phase 36 "
        "notes §5."
    )


def test_adr_0143_implementation_phase_36_footer_present() -> None:
    """ADR-0143 §Implementation (Phase 36) footer — validate_node body
    wired; validate_xref deferred per-flow per R3-PB-G."""
    _skip_if_parent_dir_missing(_ADR_DIR)
    adr = _ADR_DIR / "0143-klwritehandle.md"
    if not adr.exists():
        for candidate in _ADR_DIR.glob("0143-*.md"):
            adr = candidate
            break
    assert adr.exists(), f"ADR-0143 file missing under {_ADR_DIR}"
    content = adr.read_text(encoding="utf-8")
    assert "§Implementation (Phase 36" in content, (
        "ADR-0143 §Implementation Phase 36 footer missing — see Phase 36 "
        "notes §5 + R3-PB-G."
    )
    assert "validate_node" in content


def test_knowledge_md_validator_surface_section_present() -> None:
    """docs/dev/internals/knowledge.md amended with "Validator surface"
    section per ADR-0139 §Accept(c) + R2-PB-C."""
    _skip_if_parent_dir_missing(_INTERNALS_DIR)
    page = _INTERNALS_DIR / "knowledge.md"
    assert page.exists(), f"knowledge.md missing: {page}"
    content = page.read_text(encoding="utf-8")
    assert "Validator surface" in content, (
        "knowledge.md missing 'Validator surface' section — see Phase 36 "
        "notes §6 + R2-PB-C."
    )


# ── halvim-tree sentinels (run everywhere) ────────────────────────────


def test_phase_map_section_36_inline_amendment() -> None:
    """PHASE_MAP §Phase 36 carries §inline-amendment block (R3-PB-F)
    clarifying features-line scope wording + Tests-line "both via
    write_and_validate" wording under Option B."""
    phase_map = _REPO_ROOT / "confirmation_docs" / "PHASE_MAP.md"
    assert phase_map.exists(), f"PHASE_MAP.md missing: {phase_map}"
    content = phase_map.read_text(encoding="utf-8")
    assert "Phase 36 ship; R0 PB-1 scope-shape resolution" in content, (
        "PHASE_MAP §36 §inline-amendment block missing — see Phase 36 "
        "notes §4 + R3-PB-F."
    )
    assert "ADR-0139 §Capacity-contract" in content
    assert "capacity bodies" in content


def test_review_checklist_section_4_present() -> None:
    """review-checklist.md grows section 4 'Capacity preconditions call
    semantic validators (ADR-0139)' per R3-PB-H + R4-PB-C."""
    checklist = _REPO_ROOT / "docs" / "dev" / "review-checklist.md"
    assert checklist.exists(), f"review-checklist.md missing: {checklist}"
    content = checklist.read_text(encoding="utf-8")
    assert "## 4. Capacity preconditions call semantic validators" in content, (
        "review-checklist.md missing section 4 — see Phase 36 notes §7 + "
        "R4-PB-C."
    )
    assert "handle.validate_node" in content
    assert "ADR-0139" in content
