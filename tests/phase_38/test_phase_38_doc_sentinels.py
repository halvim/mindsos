"""Phase 38 — docs-only ship sentinels.

Extends the sentinel chain ``14a → 15a → 15b → 35 → 36 → 38``. ADRs +
the parent-tree-only artifacts live in the parent project tree
(``/Layered Intelligence/``) per Model C (``[[feedback-docs-source-
of-truth]]``); Phase 38 ships zero ADR amendments (docs-only sub-
shape per PHASE_MAP §1 §inline-amendment), so this sentinel file
anchors the **halvim-tree** changes:

  1. PHASE_MAP §38 4-clause §inline-amendment present.
  2. PHASE_MAP §1 docs-only-phase clause extension present.
  3. ``mindsos_capacity/__init__.py`` 5 deferral anchors updated
     (no more ``Phase 30+`` or ``Phase 32+`` in the deferral block).
  4. ``docs/usage/cookbook/text-realm.md`` present + correct front-matter.
  5. Three authored pages (``index.md`` + ``getting-started/
     whats-new-v4.md`` + ``concepts/glossary.md``) present + correct
     front-matter.
  6. ``confirmation_docs/PHASE_38_PAGE_INVENTORY.md`` present.

Renamed from ``test_adr_amendment_sentinels.py`` (chain ancestor
filename) to ``test_phase_38_doc_sentinels.py`` per R4-PB-C — Phase 38
ships zero ADR amendments and the prior filename misrepresented
content. Sentinel chain semantics are per-phase, not per-filename.

All sentinels run everywhere (no parent-tree dependence; Phase 38
ships nothing in the parent tree).
"""

from __future__ import annotations

from pathlib import Path


# tests/phase_38/<file> → halvim_mindsos/
_REPO_ROOT = Path(__file__).resolve().parents[2]


# ── PHASE_MAP §38 §inline-amendment sentinels ───────────────────────────


def test_phase_map_section_38_inline_amendment_present() -> None:
    """PHASE_MAP §38 carries the 4-clause §inline-amendment block per R5-PB-A."""
    phase_map = _REPO_ROOT / "confirmation_docs" / "PHASE_MAP.md"
    assert phase_map.exists(), f"PHASE_MAP.md missing: {phase_map}"
    content = phase_map.read_text(encoding="utf-8")

    # Anchor: the §inline-amendment block header (single-line; no line-wrap
    # per [[feedback-export-slate-sentinel-audit]] extension at Phase 36
    # B-36-T3 lesson).
    assert "§inline-amendment (Phase 38 ship; 4 clauses per R5-PB-A)" in content, (
        "PHASE_MAP §38 §inline-amendment header missing — see Phase 38 "
        "R5-PB-A + design log §3 for the locked 4-clause text."
    )

    # Anchor: clause 1 (features-line reframe).
    assert "Features-line reframe" in content
    assert "text-realm cookbook (read-side; transcribes Phase 32 Integration B)" in content

    # Anchor: clause 2 (pass-criterion revision).
    assert "Pass-criterion revision" in content
    assert "Strict-lift deferred to L4/L5 follow-up plan per Phase 38 R4-PB-A" in content

    # Anchor: clause 3 (§6 cookbook OOS rows).
    assert "§6 cookbook sub-table revision" in content
    assert "Phase 38 R0-PB-2" in content

    # Anchor: clause 4 (§6 Get Started + Concepts OOS rows).
    assert "§6 Get Started + Concepts sub-table revisions" in content
    assert "Phase 38 R1-PB-E" in content


def test_phase_map_section_1_design_only_phase_extension() -> None:
    """PHASE_MAP §1 design-only-phases row extended with docs-only sub-shape per R5-PB-B."""
    phase_map = _REPO_ROOT / "confirmation_docs" / "PHASE_MAP.md"
    content = phase_map.read_text(encoding="utf-8")

    assert "§inline-amendment (Phase 38 ship per R5-PB-B)" in content, (
        "PHASE_MAP §1 docs-only-phase extension missing — see Phase 38 "
        "R5-PB-B + design log §3."
    )
    # Anchor: the new sub-shape name (single-line, no wrap).
    assert "docs-only phase" in content
    # Anchor: the chain extension reference.
    assert "14a → 15a → 15b → 35 → 36 → 38" in content


# ── capacity deferral anchor sentinels (R5-PB-C) ────────────────────────


def test_capacity_deferral_anchors_updated() -> None:
    """``mindsos_capacity/__init__.py`` 5 deferral anchors updated per R5-PB-C.

    All 5 lines that previously pointed at ``Phase 30+`` / ``Phase 32+``
    (with the named carry-forward refs like ``PB-30(a)``, ``PB-27(a)``,
    ``PB-29 lock``) now point at L4 follow-up plan per Phase 38 R4-PB-D.
    Anchor #2 (``ProblemTraceSink``) was already L4-pointing and is
    untouched.
    """
    init_py = _REPO_ROOT / "mindsos_capacity" / "__init__.py"
    assert init_py.exists()
    content = init_py.read_text(encoding="utf-8")

    # The 5 updated anchors — each new line carries the
    # "deferred to L4 follow-up plan per Phase 38 R4-PB-D" suffix.
    expected = [
        "``add_type_compat`` admin API + bulk rediscover verb — deferred to\n  L4 follow-up plan per Phase 38 R4-PB-D",
        "``include_deprecated`` parameter discipline across L3 walks —\n  deferred to L4 follow-up plan per Phase 38 R4-PB-D",
        "Falkor-backed L3 bootstrap + state-file serialization — deferred\n  to L4 follow-up plan per Phase 38 R4-PB-D + R3-PB-A",
        "``--session-token`` CLI flag — deferred to L4 follow-up plan per\n  Phase 38 R4-PB-D + R3-PB-B",
        "``--install-builtins=<family,...>`` CLI flag on ``invoke`` —\n  deferred to L4 follow-up plan per Phase 38 R4-PB-D",
    ]
    for anchor in expected:
        assert anchor in content, (
            f"deferral anchor not updated to L4-pointing form:\n{anchor!r}\n"
            "see Phase 38 R5-PB-C + R4-PB-D for the lock."
        )

    # Negative assertion: the old "active anchor" pattern is gone from
    # the deferral block. "Active anchor" = a bullet item terminating
    # in `— Phase NN+` (em-dash + space, no closing quote/paren).
    # Historical citations preserved as `(was: "Phase 32+ ...")` inside
    # parentheses are allowed — they document the supersession.
    #
    # Other "Phase 32+" mentions elsewhere in the source tree (e.g.,
    # tests/phase_31/ comments) are out of scope; this sentinel only
    # enforces the __init__.py deferral block.
    import re
    deferral_block_start = content.find("Excluded (defer):")
    deferral_block_end = content.find('See ``confirmation_docs/PHASE_28_DESIGN_LOG.md')
    assert deferral_block_start > 0 and deferral_block_end > deferral_block_start, (
        "could not locate the 'Excluded (defer)' block — file structure changed?"
    )
    deferral_block = content[deferral_block_start:deferral_block_end]
    # Active-anchor pattern: em-dash + space + "Phase NN+" + end-of-line
    # OR "Phase NN+" followed by " when " / " per " / " (first" etc.
    # (NOT inside `(was: "..."`).
    active_anchor_re = re.compile(r"— Phase 3[02]\+(?:\s|$)")
    # Strip everything between `(was: "` and the next `")` so historical
    # citations don't trip the active-anchor regex.
    cleaned = re.sub(r'\(was: "[^"]*"\)', "", deferral_block, flags=re.DOTALL)
    cleaned = re.sub(r'\(was: "[^"]*$', "", cleaned, flags=re.DOTALL)  # unterminated parens (multi-line was: blocks)
    assert not active_anchor_re.search(cleaned), (
        "stale active 'Phase 30+'/'Phase 32+' anchor still in the "
        "deferral block (outside `(was: ...)` historical citations) — "
        "Phase 38 R4-PB-D was supposed to remove all of them."
    )


# ── Cookbook + authored pages + page inventory sentinels ────────────────


def test_cookbook_text_realm_present() -> None:
    """``docs/usage/cookbook/text-realm.md`` shipped at Phase 38 with correct front-matter."""
    cookbook = _REPO_ROOT / "docs" / "usage" / "cookbook" / "text-realm.md"
    assert cookbook.exists(), f"cookbook missing: {cookbook}"
    content = cookbook.read_text(encoding="utf-8")
    assert "last_confirmed_phase: 38" in content, (
        "text-realm cookbook front-matter missing last_confirmed_phase: 38 — "
        "see Phase 38 R1-PB-E + R3-PB-F."
    )
    # Anchor: cookbook is read-side only per R3-PB-A.
    assert "read-side" in content


def test_three_authored_pages_present() -> None:
    """index.md + whats-new-v4.md + glossary.md authored at Phase 38 per R1-PB-E."""
    pages = [
        _REPO_ROOT / "docs" / "index.md",
        _REPO_ROOT / "docs" / "getting-started" / "whats-new-v4.md",
        _REPO_ROOT / "docs" / "concepts" / "glossary.md",
    ]
    for page in pages:
        assert page.exists(), f"authored page missing: {page}"
        content = page.read_text(encoding="utf-8")
        assert "last_confirmed_phase: 38" in content, (
            f"{page.name} front-matter missing last_confirmed_phase: 38 — "
            f"see Phase 38 R1-PB-E."
        )


def test_phase_38_page_inventory_artifact_present() -> None:
    """``confirmation_docs/PHASE_38_PAGE_INVENTORY.md`` shipped per R5-PB-E."""
    inventory = _REPO_ROOT / "confirmation_docs" / "PHASE_38_PAGE_INVENTORY.md"
    assert inventory.exists(), f"page inventory missing: {inventory}"
    content = inventory.read_text(encoding="utf-8")
    # Anchor: the 7-column header per R5-PB-E lock.
    assert "| Path | Exists | `last_confirmed_phase` | `last_design_only_phase` | §6 highest | Drift? | Drift class |" in content, (
        "PHASE_38_PAGE_INVENTORY.md 7-column header missing — see "
        "Phase 38 R5-PB-E for the locked schema."
    )
    # Anchor: the audit declaration § at the end.
    assert "Phase 38 closing-phase audit declaration" in content
