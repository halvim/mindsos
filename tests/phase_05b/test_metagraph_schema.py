"""MetagraphSchema container tests.

Pushbacks 5-A (strict gates property typing only), 10-A (strict ships
day one), 11-A (reusable across N metagraphs), 24-hybrid (empty schema
attach semantics).
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    CypherError,
    IntergraphEdgeType,
    MetagraphSchema,
    PropertyShapeError,
    PropertyType,
    UnknownTypeError,
)


class TestMetagraphSchemaConstruction:
    def test_default_non_strict(self):
        ms = MetagraphSchema()
        assert ms.strict is False
        assert ms.intergraph_edge_types == {}

    def test_strict_kwarg(self):
        ms = MetagraphSchema(strict=True)
        assert ms.strict is True

    def test_repr(self):
        ms = MetagraphSchema(strict=True)
        assert "strict=True" in repr(ms)
        assert "intergraph_edge_types=0" in repr(ms)


class TestAddIntergraphEdgeType:
    def test_happy_path(self):
        ms = MetagraphSchema()
        iet = IntergraphEdgeType(name="EVOKES")
        ms.add_intergraph_edge_type(iet)
        assert "EVOKES" in ms.intergraph_edge_types
        assert ms.intergraph_edge_types["EVOKES"] is iet

    def test_duplicate_refused(self):
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(IntergraphEdgeType(name="EVOKES"))
        with pytest.raises(UnknownTypeError):
            ms.add_intergraph_edge_type(IntergraphEdgeType(name="EVOKES"))

    def test_invalid_cypher_name(self):
        ms = MetagraphSchema()
        with pytest.raises(CypherError):
            ms.add_intergraph_edge_type(
                IntergraphEdgeType(name="lowercase_invalid")
            )

    def test_returns_iet_for_chaining(self):
        ms = MetagraphSchema()
        iet = IntergraphEdgeType(name="X")
        result = ms.add_intergraph_edge_type(iet)
        assert result is iet


class TestRequireIntergraphEdgeType:
    def test_existing(self):
        ms = MetagraphSchema()
        iet = IntergraphEdgeType(name="EVOKES")
        ms.add_intergraph_edge_type(iet)
        assert ms.require_intergraph_edge_type("EVOKES") is iet

    def test_missing_raises(self):
        ms = MetagraphSchema()
        with pytest.raises(UnknownTypeError):
            ms.require_intergraph_edge_type("MISSING")


class TestValidateIntergraphEdge:
    def test_unconstrained_type_passes(self):
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(IntergraphEdgeType(name="X"))
        # No allowed-* constraints; any source/target accepted.
        ms.validate_intergraph_edge(
            "X", "AnyType", "AnyType", "anyrole", "anyrole",
        )

    def test_unknown_type_raises(self):
        ms = MetagraphSchema()
        with pytest.raises(UnknownTypeError):
            ms.validate_intergraph_edge(
                "MISSING", "Word", "Concept", "lexicon", "concepts",
            )

    def test_allowed_source_type_violation(self):
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="X", allowed_source_types=frozenset({"Word"}),
            )
        )
        with pytest.raises(UnknownTypeError) as exc:
            ms.validate_intergraph_edge(
                "X", "WrongType", "Concept", "lexicon", "concepts",
            )
        assert "source node type" in str(exc.value)

    def test_allowed_target_type_violation(self):
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="X", allowed_target_types=frozenset({"Concept"}),
            )
        )
        with pytest.raises(UnknownTypeError) as exc:
            ms.validate_intergraph_edge(
                "X", "Word", "WrongType", "lexicon", "concepts",
            )
        assert "target node type" in str(exc.value)

    def test_allowed_source_graph_role_violation(self):
        """Pushback 4-A — role-based source graph constraint."""
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="X", allowed_source_graphs=frozenset({"lexicon"}),
            )
        )
        with pytest.raises(UnknownTypeError) as exc:
            ms.validate_intergraph_edge(
                "X", "Word", "Concept", "wrong_role", "concepts",
            )
        assert "source graph role" in str(exc.value)

    def test_allowed_target_graph_role_violation(self):
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="X", allowed_target_graphs=frozenset({"concepts"}),
            )
        )
        with pytest.raises(UnknownTypeError):
            ms.validate_intergraph_edge(
                "X", "Word", "Concept", "lexicon", "wrong_role",
            )

    def test_role_none_unmatchable_when_constrained(self):
        """Pushback 4-A — Graph.role=None unmatchable in non-empty constraint."""
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="X", allowed_source_graphs=frozenset({"lexicon"}),
            )
        )
        with pytest.raises(UnknownTypeError):
            ms.validate_intergraph_edge(
                "X", "Word", "Concept", None, "concepts",
            )

    def test_role_none_accepted_when_empty_constraint(self):
        """Empty allowed_source_graphs accepts role=None (any role)."""
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(IntergraphEdgeType(name="X"))
        # No raise.
        ms.validate_intergraph_edge(
            "X", "Word", "Concept", None, "concepts",
        )


class TestValidateIntergraphEdgeProperties:
    def test_non_strict_early_returns(self):
        """Pushback 5-A — non-strict skips property typing entirely."""
        ms = MetagraphSchema(strict=False)
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="X",
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        # Even mismatched type passes under non-strict.
        ms.validate_intergraph_edge_properties("X", {"weight": "not-a-float"})

    def test_strict_validates(self):
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="X",
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        with pytest.raises(PropertyShapeError):
            ms.validate_intergraph_edge_properties("X", {"weight": "not-a-float"})

    def test_strict_passes_correct_type(self):
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="X",
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        ms.validate_intergraph_edge_properties("X", {"weight": 0.5})

    def test_strict_unknown_key_under_typed_vocab(self):
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="X",
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        with pytest.raises(PropertyShapeError):
            ms.validate_intergraph_edge_properties(
                "X", {"unknown_key": 1},
            )

    def test_strict_empty_property_types_allows_any(self):
        """Empty property_types map under strict = "type author opted out"."""
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_edge_type(IntergraphEdgeType(name="X"))
        # Any properties accepted because property_types is empty.
        ms.validate_intergraph_edge_properties("X", {"anything": "goes"})

    def test_strict_ref_keys_pass_through(self):
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="X",
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        # ref:* keys validated upstream as UUID strs; pass through here.
        ms.validate_intergraph_edge_properties(
            "X", {"weight": 0.5, "ref:anchor": "some-uuid"},
        )

    def test_strict_unknown_type_raises(self):
        ms = MetagraphSchema(strict=True)
        with pytest.raises(UnknownTypeError):
            ms.validate_intergraph_edge_properties(
                "MISSING", {"k": 1},
            )
