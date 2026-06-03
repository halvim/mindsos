"""Phase 43 PR1 sentinel — ADR amendment + in-place edit landing checks.

Verifies post-PR1 state of:

* ADR-0150 §amendment-5 (4 new role-graph rows + 5-item exclusion list).
* ADR-0153 §amendment-1 (L2Schema(Schema) subclass placement language).
* ADR-0151 frontmatter Related promotes 0152 + 0153 to Accepted
  (PR1 commit 6 in-place edit per design log §8.4).
* ADR-0094 §am-1 says "detector" + references
  ``check_phase_43_confidence_state.py`` (PR1 commit 6 in-place edit
  per design log §8.3).
* ADR-0143 §Implementation references gains ADR-0153 §2 cross-ref
  (PR1 commit 6 append per design log §8.5).
* ADR-0151 / 0152 / 0153 status: Accepted (existing on-disk state).
"""

from __future__ import annotations

from pathlib import Path

_ADR_DIR = Path(__file__).parents[2] / "docs" / "decisions" / "adr"


def _read(name: str) -> str:
    return (_ADR_DIR / name).read_text()


def test_adr_0150_amendment_5_present() -> None:
    body = _read("0150-l2-knowledge-lifecycle.md")
    assert "### amendment-5 (Phase 43 ship" in body
    assert "4 new role-graph rows + exclusion list" in body


def test_adr_0150_amendment_5_lists_4_new_role_graphs() -> None:
    body = _read("0150-l2-knowledge-lifecycle.md")
    for role in (
        "parameter-staging",
        "pending-promotions",
        "capacity-gaps",
        "learned-parameters",
    ):
        assert role in body, (
            f"role {role!r} missing from ADR-0150 body"
        )


def test_adr_0150_amendment_5_lists_5_item_exclusion() -> None:
    body = _read("0150-l2-knowledge-lifecycle.md")
    after_am5 = body.split("### amendment-5", 1)[1]
    for excluded in (
        "sense-correlations",
        "world-axioms",
        "training-runs",
        "fol-rules",
        "fol-ledger",
    ):
        assert excluded in after_am5, (
            f"{excluded!r} missing from §am-5 exclusion list"
        )


def test_adr_0153_amendment_1_present_with_l2schema_placement() -> None:
    body = _read("0153-l2-mutation-discipline.md")
    assert "### amendment-1 (Phase 43 ship" in body
    assert "L2Schema(Schema) subclass placement" in body
    assert "mindsos_knowledge.schemas._base.L2Schema(Schema)" in body
    # `mindsos_core.Schema` appears backtick-wrapped in the §am-1 body
    # — assertion uses the backtick-wrapped form to match the markdown
    # source literally.
    assert "`mindsos_core.Schema` is unchanged" in body


def test_adrs_151_152_153_status_accepted() -> None:
    for name in (
        "0151-l2-storage-tiers.md",
        "0152-l2-role-graph-schema-v2.md",
        "0153-l2-mutation-discipline.md",
    ):
        body = _read(name)
        assert "status: Accepted" in body, (
            f"{name}: frontmatter status missing 'Accepted'"
        )
        assert "**Status:** Accepted" in body, (
            f"{name}: header **Status:** missing 'Accepted'"
        )


def test_adr_0151_frontmatter_related_promotes_152_153_to_accepted() -> None:
    body = _read("0151-l2-storage-tiers.md")
    assert "**Related (Accepted):**" in body
    accepted_block = body.split(
        "**Related (Accepted):**", 1
    )[1].split("##", 1)[0]
    assert "0152" in accepted_block
    assert "0153" in accepted_block
    if "**Related (Proposed):**" in body:
        proposed_block = body.split(
            "**Related (Proposed):**", 1
        )[1].split("##", 1)[0]
        assert "0152" not in proposed_block
        assert "0153" not in proposed_block


def test_adr_0094_amendment_1_says_detector() -> None:
    body = _read("0094-confidence-pipeline-level.md")
    assert "detector" in body.lower()
    assert "check_phase_43_confidence_state.py" in body


def test_adr_0143_implementation_references_includes_adr_0153_cross_ref() -> None:
    body = _read("0143-kl-write-handle-pattern.md")
    assert "ADR-0153" in body
