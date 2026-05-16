"""ADR-0135 — RemovalImpact 4-field dataclass shape."""

from __future__ import annotations

from dataclasses import fields

from mindsos_core import RemovalImpact


def test_removal_impact_field_set() -> None:
    expected = {"incoming_xrefs", "incoming_ref_properties", "proceeded", "blocked_reason"}
    actual = {f.name for f in fields(RemovalImpact)}
    assert actual == expected


def test_removal_impact_default_construction() -> None:
    ri = RemovalImpact()
    assert ri.incoming_xrefs == []
    assert ri.incoming_ref_properties == []
    assert ri.proceeded is False
    assert ri.blocked_reason is None


def test_removal_impact_field_population() -> None:
    ri = RemovalImpact(
        incoming_ref_properties=[("n1", "ref:lex")],
        proceeded=True,
        blocked_reason=None,
    )
    assert ri.incoming_ref_properties == [("n1", "ref:lex")]
    assert ri.proceeded is True
