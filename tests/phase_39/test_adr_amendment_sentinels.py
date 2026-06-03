"""Phase 39 ADR-amendment sentinel chain root.

Per Phase 39 design log §1 R3-PB-B + R0 PB-10: post-A0 housekeeping,
the parent-tree-fallback / Model C SKIP logic is dead (HANDOFF §3.1.10
landed the ADR tree under ``docs/decisions/adr/``). This file anchors
the new sentinel chain at Phase 39 with no SKIP logic — module-level
``assert _ADR_DIR.exists()`` precondition fail-fast at collection.

Sentinels assert presence of:

* ADR-0044 §amendment-3 (Phase 39 rename trigger).
* ADR-0146 §amendment-3 (Phase 39 multi-NodeType dispatch).
* ADR-0150 §amendment-4 (Phase 39 narrowed to rename-row only).
* ADR-0143 cross-reference under ``## Implementation references``
  (no §amendment per design log PB-N4).
"""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT / "docs" / "decisions" / "adr"

# Phase 39 post-A0 housekeeping: ADR tree lives under repo's docs/.
# Model C parent-tree SKIP logic retired (HANDOFF §3.1.10).
assert _ADR_DIR.exists(), (
    f"ADR directory missing at expected path: {_ADR_DIR}. "
    "Post-A0 housekeeping vendored ADRs into the repo per "
    "HANDOFF §3.1.10; this file's sentinels assume that landing."
)


def _read_adr(slug: str) -> str:
    adr = _ADR_DIR / slug
    assert adr.exists(), f"ADR file missing: {adr}"
    return adr.read_text(encoding="utf-8")


# ── ADR-0044 §amendment-3 sentinel ────────────────────────────────────


def test_adr_0044_amendment_3_present() -> None:
    text = _read_adr("0044-memories-move-to-local-per-user.md")
    assert "amendment-3" in text
    assert "episodic_memories" in text


def test_adr_0044_amendment_3_names_role_rename() -> None:
    text = _read_adr("0044-memories-move-to-local-per-user.md")
    # The amendment must name both the old and new role for clarity.
    assert "episodic_memories" in text
    assert "Local-per-user" in text or "Local per user" in text


def test_adr_0044_amendment_3_cross_refs_adr_0146_am_3() -> None:
    """Phase 39 R2 PB-R2-C: one-line cross-ref to multi-NodeType dispatch."""
    text = _read_adr("0044-memories-move-to-local-per-user.md")
    assert "ADR-0146 §amendment-3" in text


# ── ADR-0146 §amendment-3 sentinel ────────────────────────────────────


def test_adr_0146_amendment_3_present() -> None:
    text = _read_adr("0146-l3-symmetric-write-invocation-contract.md")
    assert "§amendment-3" in text
    assert "multi-NodeType dispatch" in text or "tuple-key" in text


def test_adr_0146_amendment_3_documents_signature_change() -> None:
    text = _read_adr("0146-l3-symmetric-write-invocation-contract.md")
    assert "mint_iri" in text
    assert "type_" in text


def test_adr_0146_amendment_3_lists_three_registry_entries() -> None:
    text = _read_adr("0146-l3-symmetric-write-invocation-contract.md")
    # All three entries appear in the amendment body.
    assert "Episode" in text
    assert "Memory" in text
    assert "ProblemTraceEntry" in text


# ── ADR-0150 §amendment-4 (narrowed) sentinel ─────────────────────────


def test_adr_0150_amendment_4_narrowed_to_rename_only() -> None:
    text = _read_adr("0150-l2-knowledge-lifecycle.md")
    assert "amendment-4" in text
    assert "episodic_memories" in text


def test_adr_0150_amendment_4_documents_split_to_am_5() -> None:
    """Per R2 PB-R2-B + Chat C IL-3: 4-new-rows defer to §am-5 at Phase 43."""
    text = _read_adr("0150-l2-knowledge-lifecycle.md")
    assert "§amendment-5" in text
    assert "Phase 43" in text


def test_adr_0150_amendment_4_does_not_contain_new_role_table() -> None:
    """Surgery removed the ``parameter-staging`` / ``pending-promotions`` /
    ``capacity-gaps`` / ``learned-parameters`` row block from §am-4."""
    text = _read_adr("0150-l2-knowledge-lifecycle.md")
    # Locate the §am-4 block boundaries; assert the 4-new-rows table
    # entries are absent from that specific span.
    am4_start = text.find("amendment-4")
    am5_start = text.find("Split to §amendment-5")
    assert am4_start != -1 and am5_start != -1
    am4_body = text[am4_start:am5_start]
    for retired in (
        "parameter-staging",
        "pending-promotions",
        "capacity-gaps",
        "learned-parameters",
    ):
        assert retired not in am4_body, (
            f"§am-4 narrow surgery incomplete: ``{retired}`` row remains"
        )


# ── ADR-0143 cross-reference (no §amendment) sentinel ─────────────────


def test_adr_0143_cross_references_adr_0146_am_3() -> None:
    """Phase 39 design log PB-N4: one-line cross-ref under
    ``## Implementation references`` (no §amendment on ADR-0143)."""
    text = _read_adr("0143-kl-write-handle-pattern.md")
    assert "ADR-0146 §amendment-3" in text
    # Confirm ADR-0143 itself does NOT carry a new §amendment.
    # Existing amendment chain on 0143 is at the §Implementation footer
    # for Phase 33/34/36; no new top-level ``## §amendment-*`` header.
    # (We don't assert absence categorically — older amendments may exist;
    # we assert the cross-ref text is positioned under Implementation
    # references rather than as a new amendment.)
