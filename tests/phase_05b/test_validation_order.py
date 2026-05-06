"""14-step validation order tests (Pushback 16-A locked).

Each test forces a specific failure point with all higher-priority
checks satisfied, asserting the named error class fires at that step.
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    CypherError,
    Graph,
    IdentityError,
    IntergraphEdgeType,
    Metagraph,
    MetagraphSchema,
    PropertyShapeError,
    PropertyType,
    SchemaError,
    UnknownTypeError,
)


@pytest.fixture
def mg_for_order():
    mg = Metagraph(name="o")
    g_lex = Graph(name="lex", role="lexicon")
    g_cpt = Graph(name="cpt", role="concepts")
    mg.add_graph(g_lex)
    mg.add_graph(g_cpt)
    n_lex = g_lex.add_node("v1", type_name="Word")
    n_cpt = g_cpt.add_node("v2", type_name="Concept")
    return mg, g_lex, g_cpt, n_lex, n_cpt


class TestValidationOrder:
    def test_step1_source_graph_first(self, mg_for_order):
        mg, _g_lex, g_cpt, _n_lex, n_cpt = mg_for_order
        # Bad source graph + bad type — step 1 fires first.
        with pytest.raises(IdentityError) as exc:
            mg.add_intergraph_edge(
                "fake_graph", "fake_node",
                g_cpt.graph_id, n_cpt.node_id,
                "lowercase_invalid",  # would fail step 6
            )
        assert "source graph" in str(exc.value)

    def test_step2_target_graph(self, mg_for_order):
        mg, g_lex, _g_cpt, n_lex, _n_cpt = mg_for_order
        with pytest.raises(IdentityError) as exc:
            mg.add_intergraph_edge(
                g_lex.graph_id, n_lex.node_id,
                "fake_graph", "fake_node",
                "X",
            )
        assert "target graph" in str(exc.value)

    def test_step3_self_graph_before_node_check(self, mg_for_order):
        mg, g_lex, _g_cpt, n_lex, _n_cpt = mg_for_order
        # source==target, invalid node id (wouldn't be checked).
        with pytest.raises(SchemaError):
            mg.add_intergraph_edge(
                g_lex.graph_id, n_lex.node_id,
                g_lex.graph_id, "missing",
                "X",
            )

    def test_step4_source_node_before_target_node(self, mg_for_order):
        mg, g_lex, g_cpt, _n_lex, _n_cpt = mg_for_order
        # Both nodes missing — source check fires first.
        with pytest.raises(IdentityError) as exc:
            mg.add_intergraph_edge(
                g_lex.graph_id, "missing_src",
                g_cpt.graph_id, "missing_tgt",
                "X",
            )
        assert "source node" in str(exc.value)

    def test_step6_cypher_regex_after_node_checks(self, mg_for_order):
        mg, g_lex, g_cpt, n_lex, n_cpt = mg_for_order
        with pytest.raises(CypherError):
            mg.add_intergraph_edge(
                g_lex.graph_id, n_lex.node_id,
                g_cpt.graph_id, n_cpt.node_id,
                "lowercase_invalid",
            )

    def test_step7_property_shape_before_schema(self, mg_for_order):
        mg, g_lex, g_cpt, n_lex, n_cpt = mg_for_order
        # Schema attached but reserved key violation fires first.
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(IntergraphEdgeType(name="EVOKES"))
        mg.attach_schema(ms, schema_name="ms")
        with pytest.raises(PropertyShapeError):
            mg.add_intergraph_edge(
                g_lex.graph_id, n_lex.node_id,
                g_cpt.graph_id, n_cpt.node_id,
                "EVOKES",
                properties={"_compositional": True},
            )

    def test_step8_unknown_type_when_schema_attached(self, mg_for_order):
        mg, g_lex, g_cpt, n_lex, n_cpt = mg_for_order
        ms = MetagraphSchema()
        # No types registered.
        mg.attach_schema(ms, schema_name="ms")
        with pytest.raises(UnknownTypeError):
            mg.add_intergraph_edge(
                g_lex.graph_id, n_lex.node_id,
                g_cpt.graph_id, n_cpt.node_id,
                "EVOKES",
            )

    def test_step9_role_constraint_violation(self, mg_for_order):
        mg, g_lex, g_cpt, n_lex, n_cpt = mg_for_order
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="X",
                allowed_source_graphs=frozenset({"WRONG_ROLE"}),
            )
        )
        mg.attach_schema(ms, schema_name="ms")
        with pytest.raises(UnknownTypeError) as exc:
            mg.add_intergraph_edge(
                g_lex.graph_id, n_lex.node_id,
                g_cpt.graph_id, n_cpt.node_id, "X",
            )
        assert "source graph role" in str(exc.value)

    def test_step10_strict_property_typing(self, mg_for_order):
        mg, g_lex, g_cpt, n_lex, n_cpt = mg_for_order
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="X",
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        mg.attach_schema(ms, schema_name="ms")
        with pytest.raises(PropertyShapeError):
            mg.add_intergraph_edge(
                g_lex.graph_id, n_lex.node_id,
                g_cpt.graph_id, n_cpt.node_id, "X",
                properties={"weight": "not-a-float"},
            )

    def test_no_schema_skips_steps_8_through_10(self, mg_for_order):
        """Without a schema attached, type-existence/property-typing skipped."""
        mg, g_lex, g_cpt, n_lex, n_cpt = mg_for_order
        # Any type_name accepted.
        ie = mg.add_intergraph_edge(
            g_lex.graph_id, n_lex.node_id,
            g_cpt.graph_id, n_cpt.node_id, "ARBITRARY_NEVER_DECLARED",
        )
        assert ie.type_name == "ARBITRARY_NEVER_DECLARED"
