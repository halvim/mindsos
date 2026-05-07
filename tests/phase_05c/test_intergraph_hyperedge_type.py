"""Phase 05c — IntergraphHyperEdgeType frozen dataclass + ordered default."""

from __future__ import annotations

import dataclasses

import pytest

from mindsos_core import (
    IntergraphHyperEdgeType,
    PropertyType,
)


class TestFrozenDataclass:
    def test_frozen(self):
        iht = IntergraphHyperEdgeType(name="EVOKES")
        with pytest.raises(dataclasses.FrozenInstanceError):
            iht.name = "OTHER"  # type: ignore[misc]

    def test_minimal_construction(self):
        iht = IntergraphHyperEdgeType(name="EVOKES")
        assert iht.name == "EVOKES"
        assert iht.allowed_anchor_types == frozenset()
        assert iht.allowed_member_types == frozenset()
        assert iht.allowed_anchor_graphs == frozenset()
        assert iht.allowed_member_graphs == frozenset()
        # P18-A — default ordered=True.
        assert iht.ordered is True
        assert iht.property_types == {}
        assert iht.description is None


class TestOrderedDefault:
    def test_default_ordered_true(self):
        # P18-A — overrides design doc §3.3's stated False default.
        iht = IntergraphHyperEdgeType(name="T")
        assert iht.ordered is True

    def test_explicit_ordered_false(self):
        iht = IntergraphHyperEdgeType(name="T", ordered=False)
        assert iht.ordered is False


class TestPropertyTypes:
    @pytest.mark.parametrize(
        "ptype",
        [
            PropertyType.STRING, PropertyType.INT, PropertyType.FLOAT,
            PropertyType.BOOL, PropertyType.LIST_STRING, PropertyType.LIST_INT,
            PropertyType.LIST_FLOAT, PropertyType.LIST_BOOL,
        ],
    )
    def test_all_eight_property_type_variants_accepted(self, ptype):
        iht = IntergraphHyperEdgeType(
            name="T", property_types={"k": ptype},
        )
        assert iht.property_types == {"k": ptype}


class TestAllowedConstraints:
    def test_anchor_types_set_membership(self):
        iht = IntergraphHyperEdgeType(
            name="T",
            allowed_anchor_types=frozenset({"Word", "Phrase"}),
        )
        assert "Word" in iht.allowed_anchor_types
        assert "Sentence" not in iht.allowed_anchor_types

    def test_member_graphs_role_based(self):
        # Pushback 4-A precedent — graph roles, not graph names.
        iht = IntergraphHyperEdgeType(
            name="T",
            allowed_member_graphs=frozenset({"letter"}),
        )
        assert "letter" in iht.allowed_member_graphs
        # role=None unmatchable when constraint is non-empty.
        assert None not in iht.allowed_member_graphs

    def test_empty_means_any(self):
        iht = IntergraphHyperEdgeType(name="T")
        # Empty frozenset = "any role / any type accepted" (validator-side).
        assert len(iht.allowed_anchor_types) == 0
        assert len(iht.allowed_member_graphs) == 0
