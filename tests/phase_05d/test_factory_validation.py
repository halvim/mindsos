"""Phase 05d — add_metaedge / add_metahyperedge validation order tests.

Locks the order per round-7 P44 A (mirrors actual 05b
``add_intergraph_edge`` precedent at metagraph.py:735-798): containment
→ source≠target → properties → (if schema) require_*_type → validate_*
→ validate_*_properties (strict only) → register-and-construct (regex
via __post_init__).

Empty-vocab on add raises (precedent asymmetry surfaced for
IntergraphEdgeType in 05b — operator workaround: detach → add →
re-attach).
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    CypherError,
    Graph,
    IdentityError,
    MetaEdgeType,
    MetaHyperEdgeType,
    Metagraph,
    MetagraphSchema,
    PropertyShapeError,
    PropertyType,
    SchemaError,
    UnknownTypeError,
)


def _mg_with_two_graphs(role_a="ontology", role_b="lexicon"):
    mg = Metagraph(name="mg")
    g_a = Graph(name="a", role=role_a)
    g_b = Graph(name="b", role=role_b)
    mg.add_graph(g_a)
    mg.add_graph(g_b)
    return mg, g_a, g_b


class TestAddMetaedgeWithoutSchema:
    """No schema attached — validation order: containment, source≠target,
    properties, construct (regex via __post_init__).
    """

    def test_basic_add_succeeds(self):
        mg, g_a, g_b = _mg_with_two_graphs()
        me = mg.add_metaedge(g_a.graph_id, g_b.graph_id, type_name="LINKS_TO")
        assert me.type_name == "LINKS_TO"

    def test_unknown_source_graph_raises_identity_error(self):
        mg, _, g_b = _mg_with_two_graphs()
        with pytest.raises(IdentityError, match="source"):
            mg.add_metaedge("nonexistent", g_b.graph_id, type_name="X")

    def test_self_loop_refused(self):
        mg, g_a, _ = _mg_with_two_graphs()
        with pytest.raises(SchemaError, match="self-loop"):
            mg.add_metaedge(g_a.graph_id, g_a.graph_id, type_name="X")

    def test_invalid_cypher_regex_raises_at_post_init(self):
        mg, g_a, g_b = _mg_with_two_graphs()
        # Invalid regex (lowercase) — fires in __post_init__ at construct.
        with pytest.raises(CypherError):
            mg.add_metaedge(
                g_a.graph_id, g_b.graph_id, type_name="lowercase_invalid",
            )


class TestAddMetaedgeWithSchema:
    """Schema attached — full validation order applies."""

    def test_unknown_type_raises(self):
        """Empty MetaEdgeType vocab + add_metaedge → UnknownTypeError
        (P39 A precedent asymmetry)."""
        mg, g_a, g_b = _mg_with_two_graphs()
        ms = MetagraphSchema()
        mg.attach_schema(ms, schema_name="ms")
        with pytest.raises(UnknownTypeError):
            mg.add_metaedge(g_a.graph_id, g_b.graph_id, type_name="LINKS_TO")

    def test_known_type_passes(self):
        mg, g_a, g_b = _mg_with_two_graphs()
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(name="LINKS_TO"))
        mg.attach_schema(ms, schema_name="ms")
        me = mg.add_metaedge(g_a.graph_id, g_b.graph_id, type_name="LINKS_TO")
        assert me.type_name == "LINKS_TO"

    def test_role_constraint_violation_raises(self):
        mg, g_a, g_b = _mg_with_two_graphs(role_a="ontology", role_b="lexicon")
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(
            name="LINKS_TO",
            allowed_source_graphs=frozenset({"concepts"}),  # mismatch.
        ))
        mg.attach_schema(ms, schema_name="ms")
        with pytest.raises(UnknownTypeError, match="source graph role"):
            mg.add_metaedge(g_a.graph_id, g_b.graph_id, type_name="LINKS_TO")

    def test_strict_property_type_violation_raises(self):
        mg, g_a, g_b = _mg_with_two_graphs()
        ms = MetagraphSchema(strict=True)
        ms.add_meta_edge_type(MetaEdgeType(
            name="LINKS_TO",
            property_types={"weight": PropertyType.FLOAT},
        ))
        mg.attach_schema(ms, schema_name="ms")
        with pytest.raises(PropertyShapeError, match="expected float"):
            mg.add_metaedge(
                g_a.graph_id, g_b.graph_id, type_name="LINKS_TO",
                properties={"weight": "wrong"},
            )

    def test_non_strict_property_value_passes(self):
        mg, g_a, g_b = _mg_with_two_graphs()
        ms = MetagraphSchema(strict=False)
        ms.add_meta_edge_type(MetaEdgeType(
            name="LINKS_TO",
            property_types={"weight": PropertyType.FLOAT},
        ))
        mg.attach_schema(ms, schema_name="ms")
        me = mg.add_metaedge(
            g_a.graph_id, g_b.graph_id, type_name="LINKS_TO",
            properties={"weight": "wrong-but-non-strict"},
        )
        assert me.properties["weight"] == "wrong-but-non-strict"


class TestAddMetaedgeOrderingOnMultiplyBrokenInputs:
    """P44 A locks: containment first; regex via __post_init__ (last).
    Multiply-broken inputs raise the EARLIEST error per the order.
    """

    def test_containment_beats_regex(self):
        """Bad source containment + bad regex → IdentityError first."""
        mg, _, g_b = _mg_with_two_graphs()
        with pytest.raises(IdentityError):
            mg.add_metaedge("nonexistent", g_b.graph_id, type_name="bad_regex")

    def test_self_loop_beats_regex(self):
        """source==target + bad regex → SchemaError (self-loop) first."""
        mg, g_a, _ = _mg_with_two_graphs()
        with pytest.raises(SchemaError):
            mg.add_metaedge(g_a.graph_id, g_a.graph_id, type_name="bad_regex")


class TestAddMetahyperedgeWithoutSchema:
    def test_basic_add_succeeds(self):
        mg = Metagraph(name="mg")
        gs = []
        for r in ("a", "b", "c"):
            g = Graph(name=r, role=r)
            mg.add_graph(g)
            gs.append(g)
        mhe = mg.add_metahyperedge(
            [g.graph_id for g in gs], type_name="GROUPS",
        )
        assert mhe.type_name == "GROUPS"

    def test_unknown_member_graph_raises(self):
        mg = Metagraph(name="mg")
        g = Graph(name="a", role="a")
        mg.add_graph(g)
        # Need at least 2 members; add one valid and one invalid.
        with pytest.raises(IdentityError, match="member"):
            mg.add_metahyperedge(
                [g.graph_id, "nonexistent"], type_name="GROUPS",
            )


class TestAddMetahyperedgeWithSchema:
    def test_unknown_type_raises(self):
        mg = Metagraph(name="mg")
        gs = [Graph(name=r, role=r) for r in ("a", "b")]
        for g in gs:
            mg.add_graph(g)
        ms = MetagraphSchema()
        mg.attach_schema(ms, schema_name="ms")
        with pytest.raises(UnknownTypeError):
            mg.add_metahyperedge(
                [g.graph_id for g in gs], type_name="GROUPS",
            )

    def test_known_type_passes(self):
        mg = Metagraph(name="mg")
        gs = [Graph(name=r, role=r) for r in ("ontology", "lexicon")]
        for g in gs:
            mg.add_graph(g)
        ms = MetagraphSchema()
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(name="GROUPS"))
        mg.attach_schema(ms, schema_name="ms")
        mhe = mg.add_metahyperedge(
            [g.graph_id for g in gs], type_name="GROUPS",
        )
        assert mhe.type_name == "GROUPS"

    def test_member_role_violation(self):
        mg = Metagraph(name="mg")
        gs = [Graph(name=r, role=r) for r in ("ontology", "lexicon", "concepts")]
        for g in gs:
            mg.add_graph(g)
        ms = MetagraphSchema()
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(
            name="GROUPS",
            allowed_member_graphs=frozenset({"ontology", "lexicon"}),
        ))
        mg.attach_schema(ms, schema_name="ms")
        with pytest.raises(UnknownTypeError, match="member graph role"):
            mg.add_metahyperedge(
                [g.graph_id for g in gs], type_name="GROUPS",
            )
