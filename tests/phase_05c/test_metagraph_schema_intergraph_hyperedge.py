"""Phase 05c — MetagraphSchema vocab + validator extensions for hyperedges."""

from __future__ import annotations

import pytest

from mindsos_core import (
    CypherError,
    IntergraphHyperEdgeType,
    MetagraphSchema,
    PropertyShapeError,
    PropertyType,
    UnknownTypeError,
)


class TestRegistration:
    def test_add_intergraph_hyperedge_type_happy(self):
        ms = MetagraphSchema()
        iht = IntergraphHyperEdgeType(name="COMPOSED_OF")
        result = ms.add_intergraph_hyperedge_type(iht)
        assert result is iht
        assert "COMPOSED_OF" in ms.intergraph_hyperedge_types

    def test_duplicate_name_refused(self):
        ms = MetagraphSchema()
        ms.add_intergraph_hyperedge_type(IntergraphHyperEdgeType(name="T"))
        with pytest.raises(UnknownTypeError, match="already registered"):
            ms.add_intergraph_hyperedge_type(IntergraphHyperEdgeType(name="T"))

    def test_invalid_cypher_name_refused(self):
        ms = MetagraphSchema()
        with pytest.raises(CypherError):
            ms.add_intergraph_hyperedge_type(
                IntergraphHyperEdgeType(name="lowercase_invalid")
            )

    def test_intergraph_edge_and_hyperedge_namespaces_independent(self):
        # Same name in both vocabs is permitted (Phase 05c does not
        # cross-check; documented in metagraph_schema docstring).
        from mindsos_core import IntergraphEdgeType
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(IntergraphEdgeType(name="EVOKES"))
        # Hyperedge vocab can also register EVOKES.
        ms.add_intergraph_hyperedge_type(
            IntergraphHyperEdgeType(name="EVOKES")
        )
        assert "EVOKES" in ms.intergraph_edge_types
        assert "EVOKES" in ms.intergraph_hyperedge_types


class TestRequire:
    def test_require_happy(self):
        ms = MetagraphSchema()
        iht = IntergraphHyperEdgeType(name="T")
        ms.add_intergraph_hyperedge_type(iht)
        result = ms.require_intergraph_hyperedge_type("T")
        assert result is iht

    def test_require_unknown_raises(self):
        ms = MetagraphSchema()
        with pytest.raises(UnknownTypeError, match="Unknown intergraph hyperedge"):
            ms.require_intergraph_hyperedge_type("MISSING")


class TestValidate:
    def test_validate_happy(self):
        ms = MetagraphSchema()
        ms.add_intergraph_hyperedge_type(
            IntergraphHyperEdgeType(
                name="COMPOSED_OF",
                allowed_anchor_types=frozenset({"Word"}),
                allowed_member_types=frozenset({"Letter"}),
                allowed_anchor_graphs=frozenset({"word"}),
                allowed_member_graphs=frozenset({"letter"}),
            )
        )
        # Validator does not raise on satisfying input.
        ms.validate_intergraph_hyperedge(
            type_name="COMPOSED_OF",
            anchor_node_types=["Word"],
            member_node_types=["Letter", "Letter", "Letter"],
            anchor_graph_roles=["word"],
            member_graph_roles=["letter", "letter", "letter"],
        )

    def test_validate_anchor_type_rejection(self):
        ms = MetagraphSchema()
        ms.add_intergraph_hyperedge_type(
            IntergraphHyperEdgeType(
                name="T",
                allowed_anchor_types=frozenset({"Word"}),
            )
        )
        with pytest.raises(UnknownTypeError, match="anchor node type"):
            ms.validate_intergraph_hyperedge(
                type_name="T",
                anchor_node_types=["Sentence"],  # not in {"Word"}
                member_node_types=["X", "Y"],
                anchor_graph_roles=[None],
                member_graph_roles=[None, None],
            )

    def test_validate_member_type_rejection(self):
        ms = MetagraphSchema()
        ms.add_intergraph_hyperedge_type(
            IntergraphHyperEdgeType(
                name="T",
                allowed_member_types=frozenset({"Letter"}),
            )
        )
        with pytest.raises(UnknownTypeError, match="member node type"):
            ms.validate_intergraph_hyperedge(
                type_name="T",
                anchor_node_types=["Word"],
                member_node_types=["Letter", "Phoneme"],  # second mismatch
                anchor_graph_roles=[None],
                member_graph_roles=[None, None],
            )

    def test_validate_anchor_graph_role_rejection(self):
        ms = MetagraphSchema()
        ms.add_intergraph_hyperedge_type(
            IntergraphHyperEdgeType(
                name="T",
                allowed_anchor_graphs=frozenset({"word"}),
            )
        )
        with pytest.raises(UnknownTypeError, match="anchor graph role"):
            ms.validate_intergraph_hyperedge(
                type_name="T",
                anchor_node_types=["X"],
                member_node_types=["Y", "Z"],
                anchor_graph_roles=["sentence"],  # not "word"
                member_graph_roles=[None, None],
            )

    def test_validate_member_graph_role_none_unmatchable_when_constrained(self):
        # Per Pushback 4-A: role=None doesn't satisfy a non-empty constraint.
        ms = MetagraphSchema()
        ms.add_intergraph_hyperedge_type(
            IntergraphHyperEdgeType(
                name="T",
                allowed_member_graphs=frozenset({"letter"}),
            )
        )
        with pytest.raises(UnknownTypeError, match="member graph role"):
            ms.validate_intergraph_hyperedge(
                type_name="T",
                anchor_node_types=["X"],
                member_node_types=["Y", "Z"],
                anchor_graph_roles=[None],
                member_graph_roles=[None, None],
            )

    def test_validate_empty_constraint_means_any(self):
        # Empty allowed_*_types / allowed_*_graphs accept anything.
        ms = MetagraphSchema()
        ms.add_intergraph_hyperedge_type(IntergraphHyperEdgeType(name="T"))
        ms.validate_intergraph_hyperedge(
            type_name="T",
            anchor_node_types=["AnyType"],
            member_node_types=["AnyType", "AnyType"],
            anchor_graph_roles=[None],
            member_graph_roles=[None, None],
        )

    def test_validate_unknown_type_raises(self):
        ms = MetagraphSchema()
        with pytest.raises(UnknownTypeError, match="Unknown intergraph hyperedge"):
            ms.validate_intergraph_hyperedge(
                type_name="MISSING",
                anchor_node_types=["X"],
                member_node_types=["Y", "Z"],
                anchor_graph_roles=[None],
                member_graph_roles=[None, None],
            )


class TestValidateProperties:
    def test_strict_off_no_check(self):
        # Pushback 5-A precedent — validate_*_properties early-returns.
        ms = MetagraphSchema(strict=False)
        ms.add_intergraph_hyperedge_type(
            IntergraphHyperEdgeType(
                name="T",
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        # Even with wrong type, non-strict skips.
        ms.validate_intergraph_hyperedge_properties("T", {"weight": "bad"})

    def test_strict_on_type_match(self):
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_hyperedge_type(
            IntergraphHyperEdgeType(
                name="T",
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        ms.validate_intergraph_hyperedge_properties("T", {"weight": 0.5})

    def test_strict_on_type_mismatch(self):
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_hyperedge_type(
            IntergraphHyperEdgeType(
                name="T",
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        with pytest.raises(PropertyShapeError):
            ms.validate_intergraph_hyperedge_properties(
                "T", {"weight": "not_a_float"},
            )

    def test_strict_on_undeclared_key(self):
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_hyperedge_type(
            IntergraphHyperEdgeType(
                name="T",
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        with pytest.raises(PropertyShapeError, match="not.*declared"):
            ms.validate_intergraph_hyperedge_properties(
                "T", {"weight": 0.5, "extra": "boom"},
            )

    def test_strict_with_no_property_types_accepts_anything(self):
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_hyperedge_type(IntergraphHyperEdgeType(name="T"))
        # Empty property_types means type author opted out.
        ms.validate_intergraph_hyperedge_properties("T", {"any": "value"})

    def test_ref_keys_skipped_under_strict(self):
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_hyperedge_type(
            IntergraphHyperEdgeType(
                name="T",
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        # ref:* keys bypass strict-typing per validator contract.
        ms.validate_intergraph_hyperedge_properties(
            "T", {"weight": 0.5, "ref:foo": "some-uuid-string"},
        )
