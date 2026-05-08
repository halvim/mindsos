"""Phase 05d — MetagraphSchema validator tests for meta-vocab.

Locks the validator semantics per round-7 row §B: type-existence
ALWAYS runs (independent of strict); role-only constraints
(allowed_*_graphs) — no node-type constraints. Empty frozenset =
"any". ``Graph.role=None`` unmatchable when constraint non-empty.
P38 B informational cross-vocab hint (no editorial recommendation).
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    IntergraphEdgeType,
    IntergraphHyperEdgeType,
    MetaEdgeType,
    MetaHyperEdgeType,
    MetagraphSchema,
    PropertyShapeError,
    PropertyType,
    UnknownTypeError,
)


class TestRequireMetaEdgeType:
    def test_known_type_returns(self):
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(name="X"))
        assert ms.require_meta_edge_type("X").name == "X"

    def test_unknown_raises(self):
        ms = MetagraphSchema()
        with pytest.raises(UnknownTypeError, match="Unknown meta-edge type"):
            ms.require_meta_edge_type("NOPE")

    def test_unknown_with_sibling_in_intergraph_edge_type_emits_hint(self):
        """P38 B — informational hint, no editorial recommendation."""
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(IntergraphEdgeType(name="X"))
        with pytest.raises(UnknownTypeError) as exc:
            ms.require_meta_edge_type("X")
        msg = str(exc.value)
        # Hint mentions the sibling vocab.
        assert "IntergraphEdgeType" in msg
        # Hint does NOT recommend a course of action.
        assert "segregation" not in msg
        assert "should" not in msg


class TestRequireMetaHyperEdgeType:
    def test_known_type_returns(self):
        ms = MetagraphSchema()
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(name="X"))
        assert ms.require_meta_hyperedge_type("X").name == "X"

    def test_unknown_raises(self):
        ms = MetagraphSchema()
        with pytest.raises(UnknownTypeError, match="Unknown meta-hyperedge type"):
            ms.require_meta_hyperedge_type("NOPE")

    def test_unknown_with_sibling_in_intergraph_hyperedge_type_emits_hint(self):
        """P38 B — informational hint, no editorial recommendation."""
        ms = MetagraphSchema()
        ms.add_intergraph_hyperedge_type(IntergraphHyperEdgeType(name="X"))
        with pytest.raises(UnknownTypeError) as exc:
            ms.require_meta_hyperedge_type("X")
        msg = str(exc.value)
        assert "IntergraphHyperEdgeType" in msg
        assert "segregation" not in msg


class TestValidateMetaEdge:
    def test_unknown_type_raises(self):
        ms = MetagraphSchema()
        with pytest.raises(UnknownTypeError):
            ms.validate_meta_edge("X", "ontology", "lexicon")

    def test_known_type_no_role_constraint_passes(self):
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(name="X"))
        # Empty allowed_*_graphs = any.
        ms.validate_meta_edge("X", "ontology", "lexicon")
        ms.validate_meta_edge("X", None, None)
        ms.validate_meta_edge("X", "anything", "anything")

    def test_source_role_constraint_violation(self):
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(
            name="X",
            allowed_source_graphs=frozenset({"ontology"}),
        ))
        with pytest.raises(UnknownTypeError, match="source graph role"):
            ms.validate_meta_edge("X", "lexicon", "concepts")

    def test_target_role_constraint_violation(self):
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(
            name="X",
            allowed_target_graphs=frozenset({"lexicon"}),
        ))
        with pytest.raises(UnknownTypeError, match="target graph role"):
            ms.validate_meta_edge("X", "ontology", "concepts")

    def test_role_none_unmatchable_when_constraint_non_empty(self):
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(
            name="X",
            allowed_source_graphs=frozenset({"ontology"}),
        ))
        # Per row §A: Graph.role=None is unmatchable when constraint
        # non-empty (Python set membership semantics).
        with pytest.raises(UnknownTypeError):
            ms.validate_meta_edge("X", None, "any")

    def test_role_none_passes_when_constraint_empty(self):
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(name="X"))
        # Empty constraint = any, including None.
        ms.validate_meta_edge("X", None, None)


class TestValidateMetaHyperEdge:
    def test_unknown_type_raises(self):
        ms = MetagraphSchema()
        with pytest.raises(UnknownTypeError):
            ms.validate_meta_hyperedge("X", ["any"])

    def test_known_type_no_constraint_passes(self):
        ms = MetagraphSchema()
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(name="X"))
        ms.validate_meta_hyperedge("X", ["a", "b", "c"])
        ms.validate_meta_hyperedge("X", [None, None])
        ms.validate_meta_hyperedge("X", [])

    def test_member_role_constraint_violation(self):
        ms = MetagraphSchema()
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(
            name="X",
            allowed_member_graphs=frozenset({"ontology", "lexicon"}),
        ))
        with pytest.raises(UnknownTypeError, match="member graph role"):
            ms.validate_meta_hyperedge("X", ["ontology", "concepts"])

    def test_member_role_constraint_passes(self):
        ms = MetagraphSchema()
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(
            name="X",
            allowed_member_graphs=frozenset({"ontology", "lexicon"}),
        ))
        ms.validate_meta_hyperedge("X", ["ontology", "lexicon", "ontology"])

    def test_role_none_unmatchable(self):
        ms = MetagraphSchema()
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(
            name="X",
            allowed_member_graphs=frozenset({"ontology"}),
        ))
        with pytest.raises(UnknownTypeError):
            ms.validate_meta_hyperedge("X", ["ontology", None])


class TestValidateMetaEdgeProperties:
    def test_non_strict_early_returns(self):
        ms = MetagraphSchema(strict=False)
        ms.add_meta_edge_type(MetaEdgeType(
            name="X",
            property_types={"weight": PropertyType.FLOAT},
        ))
        # Wrong type but non-strict — passes silently.
        ms.validate_meta_edge_properties("X", {"weight": "not-a-float"})

    def test_strict_known_property_correct_type(self):
        ms = MetagraphSchema(strict=True)
        ms.add_meta_edge_type(MetaEdgeType(
            name="X",
            property_types={"weight": PropertyType.FLOAT},
        ))
        ms.validate_meta_edge_properties("X", {"weight": 0.5})

    def test_strict_known_property_wrong_type(self):
        ms = MetagraphSchema(strict=True)
        ms.add_meta_edge_type(MetaEdgeType(
            name="X",
            property_types={"weight": PropertyType.FLOAT},
        ))
        with pytest.raises(PropertyShapeError, match="expected float"):
            ms.validate_meta_edge_properties("X", {"weight": "no"})

    def test_strict_undeclared_property_with_typed_map_raises(self):
        ms = MetagraphSchema(strict=True)
        ms.add_meta_edge_type(MetaEdgeType(
            name="X",
            property_types={"weight": PropertyType.FLOAT},
        ))
        with pytest.raises(PropertyShapeError, match="not.*declared"):
            ms.validate_meta_edge_properties("X", {"unknown": 1})

    def test_strict_empty_property_types_accepts_anything(self):
        ms = MetagraphSchema(strict=True)
        ms.add_meta_edge_type(MetaEdgeType(name="X"))
        # Empty property_types = type author opted out of strict typing
        # for this type.
        ms.validate_meta_edge_properties("X", {"anything": "goes"})

    def test_ref_prefix_skipped(self):
        ms = MetagraphSchema(strict=True)
        ms.add_meta_edge_type(MetaEdgeType(
            name="X",
            property_types={"weight": PropertyType.FLOAT},
        ))
        # ref:* validated upstream as UUID-shaped str; skipped here.
        ms.validate_meta_edge_properties(
            "X", {"weight": 0.5, "ref:other": "uuid-shaped"}
        )


class TestValidateMetaHyperEdgeProperties:
    def test_non_strict_early_returns(self):
        ms = MetagraphSchema(strict=False)
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(
            name="X",
            property_types={"strength": PropertyType.FLOAT},
        ))
        ms.validate_meta_hyperedge_properties("X", {"strength": "wrong"})

    def test_strict_correct_type(self):
        ms = MetagraphSchema(strict=True)
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(
            name="X",
            property_types={"strength": PropertyType.FLOAT},
        ))
        ms.validate_meta_hyperedge_properties("X", {"strength": 0.5})

    def test_strict_wrong_type_raises(self):
        ms = MetagraphSchema(strict=True)
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(
            name="X",
            property_types={"strength": PropertyType.FLOAT},
        ))
        with pytest.raises(PropertyShapeError, match="expected float"):
            ms.validate_meta_hyperedge_properties("X", {"strength": "wrong"})


class TestRepr:
    def test_repr_includes_meta_vocab_counts(self):
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(name="X"))
        ms.add_meta_edge_type(MetaEdgeType(name="Y"))
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(name="Z"))
        s = repr(ms)
        assert "meta_edge_types=2" in s
        assert "meta_hyperedge_types=1" in s
