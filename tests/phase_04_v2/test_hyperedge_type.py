"""Phase 04-v2 — `HyperEdgeType` dataclass.

Locks: MC-2, HET-1, AME-1.
"""

from __future__ import annotations

from mindsos_core import HyperEdgeType, PropertyType


def test_hyperedge_type_default_empty_allowed_member_types():
    """AME-1 — empty `allowed_member_types` permitted (mirrors EdgeType)."""
    het = HyperEdgeType(name="MEMBERS")
    assert het.name == "MEMBERS"
    assert het.allowed_member_types == frozenset()
    assert het.property_types == {}
    assert het.description is None


def test_hyperedge_type_with_constraints():
    """HET-1 — list[str] of allowed member types; symmetric across all members."""
    het = HyperEdgeType(
        name="ATTENDS",
        allowed_member_types=frozenset({"Person", "School"}),
        property_types={"year": PropertyType.INT},
        description="Person + School pair as event.",
    )
    assert het.allowed_member_types == frozenset({"Person", "School"})
    assert het.property_types == {"year": PropertyType.INT}
    assert het.description == "Person + School pair as event."


def test_hyperedge_type_is_frozen_dataclass():
    """Frozen — same convention as NodeType / EdgeType."""
    import dataclasses
    het = HyperEdgeType(name="X")
    try:
        het.name = "Y"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("HyperEdgeType should be frozen")
