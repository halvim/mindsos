"""Phase 09 P53 reversal — XRef restores target_stale + deprecated_at fields."""

from __future__ import annotations

from dataclasses import fields

from mindsos_core.models.xref import XRef


def test_xref_field_count_is_10() -> None:
    """8 Phase 09 fields + 2 Phase 10 restored = 10."""
    actual = {f.name for f in fields(XRef)}
    expected = {
        "source_metagraph_id", "source_id",
        "target_metagraph_id", "target_role", "target_id",
        "ref_type", "xref_id", "properties",
        # Phase 10 P53 reversal:
        "target_stale", "deprecated_at",
    }
    assert actual == expected


def test_xref_target_stale_default_false() -> None:
    x = XRef(
        source_metagraph_id="mg1", source_id="s",
        target_metagraph_id="mg2", target_role="r", target_id="t",
        ref_type="SPECIALISES",
    )
    assert x.target_stale is False


def test_xref_deprecated_at_default_none() -> None:
    x = XRef(
        source_metagraph_id="mg1", source_id="s",
        target_metagraph_id="mg2", target_role="r", target_id="t",
        ref_type="SPECIALISES",
    )
    assert x.deprecated_at is None


def test_xref_does_not_have_disputed_at() -> None:
    """ADR-0128 amendment-3: XRef has no disputed_at."""
    actual = {f.name for f in fields(XRef)}
    assert "disputed_at" not in actual
