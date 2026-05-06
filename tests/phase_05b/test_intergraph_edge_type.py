"""IntergraphEdgeType frozen dataclass tests (Pushback 4-A role-based).

Mirrors Phase 04 EdgeType + adds role-based graph-level constraints.
"""

from __future__ import annotations

import pytest

from mindsos_core import IntergraphEdgeType, PropertyType


class TestIntergraphEdgeTypeDataclass:
    def test_default_construction(self):
        iet = IntergraphEdgeType(name="X")
        assert iet.name == "X"
        assert iet.allowed_source_types == frozenset()
        assert iet.allowed_target_types == frozenset()
        assert iet.allowed_source_graphs == frozenset()
        assert iet.allowed_target_graphs == frozenset()
        assert iet.property_types == {}
        assert iet.description is None

    def test_full_construction(self):
        iet = IntergraphEdgeType(
            name="EVOKES",
            allowed_source_types=frozenset({"Word"}),
            allowed_target_types=frozenset({"Concept"}),
            allowed_source_graphs=frozenset({"lexicon"}),
            allowed_target_graphs=frozenset({"concepts"}),
            property_types={"weight": PropertyType.FLOAT},
            description="Lexicon → Concept evocation.",
        )
        assert iet.name == "EVOKES"
        assert "Word" in iet.allowed_source_types
        assert "lexicon" in iet.allowed_source_graphs
        assert iet.property_types == {"weight": PropertyType.FLOAT}
        assert iet.description == "Lexicon → Concept evocation."

    def test_frozen_dataclass_immutable(self):
        iet = IntergraphEdgeType(name="X")
        with pytest.raises(Exception):
            # frozen dataclass refuses any field assignment.
            iet.name = "Y"  # type: ignore[misc]

    def test_repr(self):
        iet = IntergraphEdgeType(name="EVOKES")
        assert "EVOKES" in repr(iet)

    def test_role_based_empty_means_any(self):
        """Pushback 4-A: empty frozenset = any role accepted (matches EdgeType)."""
        iet = IntergraphEdgeType(name="X")
        assert iet.allowed_source_graphs == frozenset()
        # The semantic is enforced in MetagraphSchema.validate_intergraph_edge,
        # not in the dataclass itself. This test asserts the empty-set
        # default is what we expect.

    def test_role_based_role_none_unmatchable_when_constrained(self):
        """Pushback 4-A: ``Graph.role=None`` not in non-empty frozenset."""
        iet = IntergraphEdgeType(
            name="X",
            allowed_source_graphs=frozenset({"lexicon"}),
        )
        # Python set semantics: None not in frozenset of strings.
        assert None not in iet.allowed_source_graphs

    def test_property_types_all_8_variants(self):
        iet = IntergraphEdgeType(
            name="X",
            property_types={
                "s": PropertyType.STRING,
                "i": PropertyType.INT,
                "f": PropertyType.FLOAT,
                "b": PropertyType.BOOL,
                "ls": PropertyType.LIST_STRING,
                "li": PropertyType.LIST_INT,
                "lf": PropertyType.LIST_FLOAT,
                "lb": PropertyType.LIST_BOOL,
            },
        )
        assert len(iet.property_types) == 8
