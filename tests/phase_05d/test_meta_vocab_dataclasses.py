"""Phase 05d — MetaEdgeType + MetaHyperEdgeType dataclass tests.

Locks the dataclass shape per round-7 P31 A row §A: frozen dataclasses;
``MetaHyperEdgeType`` deliberately omits ``ordered`` (P1 C); neither
carries ``allowed_*_types`` (metaedge primitives connect graphs, not
nodes).
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    CypherError,
    MetaEdgeType,
    MetaHyperEdgeType,
    MetagraphSchema,
    PropertyType,
    UnknownTypeError,
)


class TestMetaEdgeType:
    def test_minimal_construction(self):
        met = MetaEdgeType(name="LINKS_TO")
        assert met.name == "LINKS_TO"
        assert met.allowed_source_graphs == frozenset()
        assert met.allowed_target_graphs == frozenset()
        assert met.property_types == {}
        assert met.description is None

    def test_repr(self):
        assert repr(MetaEdgeType(name="X")) == "MetaEdgeType('X')"

    def test_frozen(self):
        met = MetaEdgeType(name="LINKS_TO")
        with pytest.raises(Exception):
            met.name = "MUTATED"  # type: ignore[misc]

    def test_full_construction(self):
        met = MetaEdgeType(
            name="REFERENCES",
            allowed_source_graphs=frozenset({"ontology"}),
            allowed_target_graphs=frozenset({"lexicon", "concepts"}),
            property_types={"weight": PropertyType.FLOAT},
            description="Cross-graph reference relationship.",
        )
        assert met.allowed_source_graphs == {"ontology"}
        assert met.allowed_target_graphs == {"lexicon", "concepts"}
        assert met.property_types["weight"] == PropertyType.FLOAT
        assert met.description == "Cross-graph reference relationship."

    def test_no_allowed_types_fields(self):
        """Per row §A, MetaEdgeType has NO allowed_*_types (graphs not nodes)."""
        met = MetaEdgeType(name="X")
        assert not hasattr(met, "allowed_source_types")
        assert not hasattr(met, "allowed_target_types")


class TestMetaHyperEdgeType:
    def test_minimal_construction(self):
        mht = MetaHyperEdgeType(name="GROUPS")
        assert mht.name == "GROUPS"
        assert mht.allowed_member_graphs == frozenset()
        assert mht.property_types == {}
        assert mht.description is None

    def test_repr(self):
        assert repr(MetaHyperEdgeType(name="X")) == "MetaHyperEdgeType('X')"

    def test_frozen(self):
        mht = MetaHyperEdgeType(name="GROUPS")
        with pytest.raises(Exception):
            mht.name = "MUTATED"  # type: ignore[misc]

    def test_no_ordered_field(self):
        """Per row P1 C, MetaHyperEdgeType has NO ordered field.

        Rationale: MetaHyperEdge.graph_ids enforces uniqueness at
        ``__post_init__``; the cat=c+a+t / "letter" rationale that
        motivated ordered=True on IntergraphHyperEdgeType applies only
        to node-level n-ary edges. See memory
        ``reference_mindsos_four_edge_primitives.md``.
        """
        mht = MetaHyperEdgeType(name="X")
        assert not hasattr(mht, "ordered")

    def test_no_allowed_types_field(self):
        """Per row §A, MetaHyperEdgeType has NO allowed_member_types."""
        mht = MetaHyperEdgeType(name="X")
        assert not hasattr(mht, "allowed_member_types")
        assert not hasattr(mht, "allowed_anchor_types")
        assert not hasattr(mht, "allowed_anchor_graphs")

    def test_full_construction(self):
        mht = MetaHyperEdgeType(
            name="UNIFIES",
            allowed_member_graphs=frozenset({"ontology", "lexicon"}),
            property_types={"strength": PropertyType.FLOAT},
            description="Cross-domain unification edge.",
        )
        assert mht.allowed_member_graphs == {"ontology", "lexicon"}


class TestMetaTypeRegexValidation:
    def test_meta_edge_type_invalid_name_raises_at_registration(self):
        ms = MetagraphSchema()
        with pytest.raises(CypherError):
            ms.add_meta_edge_type(MetaEdgeType(name="lowercase_invalid"))

    def test_meta_hyperedge_type_invalid_name_raises_at_registration(self):
        ms = MetagraphSchema()
        with pytest.raises(CypherError):
            ms.add_meta_hyperedge_type(MetaHyperEdgeType(name="123_LEADS_DIGIT"))

    def test_meta_edge_type_valid_name_registers(self):
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(name="VALID_NAME"))
        assert "VALID_NAME" in ms.meta_edge_types

    def test_duplicate_meta_edge_type_raises(self):
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(name="X"))
        with pytest.raises(UnknownTypeError, match="already registered"):
            ms.add_meta_edge_type(MetaEdgeType(name="X"))

    def test_duplicate_meta_hyperedge_type_raises(self):
        ms = MetagraphSchema()
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(name="X"))
        with pytest.raises(UnknownTypeError, match="already registered"):
            ms.add_meta_hyperedge_type(MetaHyperEdgeType(name="X"))


class TestCrossVocabSameNameAllowed:
    """Per round-7 P2 A locked from round 1 — same name across vocabs OK."""

    def test_same_name_in_meta_edge_and_intergraph_edge(self):
        from mindsos_core import IntergraphEdgeType

        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(IntergraphEdgeType(name="X"))
        ms.add_meta_edge_type(MetaEdgeType(name="X"))
        # Both registered; tracked in separate dicts.
        assert "X" in ms.intergraph_edge_types
        assert "X" in ms.meta_edge_types

    def test_same_name_across_all_four_vocabs(self):
        from mindsos_core import IntergraphEdgeType, IntergraphHyperEdgeType

        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(IntergraphEdgeType(name="X"))
        ms.add_intergraph_hyperedge_type(IntergraphHyperEdgeType(name="X"))
        ms.add_meta_edge_type(MetaEdgeType(name="X"))
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(name="X"))
        assert len(ms.intergraph_edge_types) == 1
        assert len(ms.intergraph_hyperedge_types) == 1
        assert len(ms.meta_edge_types) == 1
        assert len(ms.meta_hyperedge_types) == 1
