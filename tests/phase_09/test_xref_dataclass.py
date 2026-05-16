"""XRef dataclass — field defaults + hash/eq/repr (Phase 09 P53 + P57)."""

from __future__ import annotations

import pytest

from mindsos_core.models.xref import XRef


def test_required_fields_kw_only_no_positional():
    """P57 — kw_only=True; positional construction MUST fail."""
    with pytest.raises(TypeError):
        XRef("mg1", "n1", "mg2", "lex", "n9", "SPECIALISES")  # type: ignore[misc]


def test_kw_construction_minimal():
    x = XRef(
        source_metagraph_id="mg-src",
        source_id="src-n1",
        target_metagraph_id="mg-tgt",
        target_role="lexicon",
        target_id="tgt-n1",
        ref_type="SPECIALISES",
    )
    assert x.source_metagraph_id == "mg-src"
    assert x.source_id == "src-n1"
    assert x.target_metagraph_id == "mg-tgt"
    assert x.target_role == "lexicon"
    assert x.target_id == "tgt-n1"
    assert x.ref_type == "SPECIALISES"
    # Default xref_id minted as UUID4 (string, length 36).
    assert isinstance(x.xref_id, str) and len(x.xref_id) == 36
    # Default empty properties.
    assert x.properties == {}


def test_target_stale_and_deprecated_at_p53_reversal_phase_10():
    """Phase 10 B-10-T3 — Phase 09 P53 DROPPED target_stale + deprecated_at;
    Phase 10 P53 REVERSAL restored them (P53 reversal per design lock M5 +
    PHASE_MAP §Phase 10 row). Audit-class
    feedback_phase_baseline_literal_audit.md.
    """
    x = XRef(
        source_metagraph_id="mg-src",
        source_id="n1",
        target_metagraph_id="mg-tgt",
        target_role="lex",
        target_id="t1",
        ref_type="SPECIALISES",
    )
    # Fields restored in Phase 10 with default-False / default-None.
    assert hasattr(x, "target_stale")
    assert hasattr(x, "deprecated_at")
    assert x.target_stale is False
    assert x.deprecated_at is None


def test_explicit_xref_id_preserved():
    x = XRef(
        source_metagraph_id="mg-src",
        source_id="n1",
        target_metagraph_id="mg-tgt",
        target_role="lex",
        target_id="t1",
        ref_type="SPECIALISES",
        xref_id="explicit-xid-1",
    )
    assert x.xref_id == "explicit-xid-1"


def test_eq_and_hash_keyed_by_xref_id():
    x1 = XRef(
        source_metagraph_id="mg",
        source_id="a",
        target_metagraph_id="mg2",
        target_role="r",
        target_id="b",
        ref_type="SPECIALISES",
        xref_id="same",
    )
    x2 = XRef(
        source_metagraph_id="mg",
        source_id="DIFFERENT",  # different content
        target_metagraph_id="mg2",
        target_role="r",
        target_id="b",
        ref_type="SPECIALISES",
        xref_id="same",  # same id
    )
    x3 = XRef(
        source_metagraph_id="mg",
        source_id="a",
        target_metagraph_id="mg2",
        target_role="r",
        target_id="b",
        ref_type="SPECIALISES",
        xref_id="other",
    )
    # Eq: same xref_id ⇒ equal even if content differs.
    assert x1 == x2
    assert x1 != x3
    # Hash: same xref_id ⇒ same hash.
    assert hash(x1) == hash(x2)
    assert {x1, x2} == {x1}


def test_repr_truncates_ids_to_8_chars():
    x = XRef(
        source_metagraph_id="aaaa-bbbb-cccc",
        source_id="src1234567890",
        target_metagraph_id="tgt12345abcdef",
        target_role="lexicon",
        target_id="t9876543",
        ref_type="SPECIALISES",
        xref_id="xidlong-abcdef-12345",
    )
    r = repr(x)
    assert "src12345" in r
    assert "tgt12345" in r
    assert "lexicon" in r
    assert "SPECIALISES" in r
    assert "xidlong-" in r
    # No STALE flag in P09 repr (P53 dropped target_stale).
    assert "STALE" not in r
