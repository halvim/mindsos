"""Metagraph.attach_schema / detach_schema tests.

Pushbacks 7-A (eager validation), 9-A (skips metaedges/metahyperedges),
12-A (one attached at most), 17-A (atomic precheck), 19-B (role mismatch
warning at CLI layer; here we test the model behavior), 24-hybrid
(empty-vocab attach), 29-A (atomic on raise), 32-D (re-attach is fresh
validation).
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    Graph,
    IdentityError,
    IntergraphEdgeType,
    Metagraph,
    MetagraphSchema,
    PropertyShapeError,
    PropertyType,
    UnknownTypeError,
)


class TestAttachSchemaHappyPath:
    def test_empty_metagraph_empty_schema(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ms = MetagraphSchema()
        # Pushback 24-hybrid: empty schema attach succeeds in non-strict.
        f["mg"].attach_schema(ms, schema_name="empty")
        assert f["mg"].schema_name == "empty"
        assert f["mg"].schema is ms

    def test_attach_validates_existing_intergraph_edges(self, mg_with_two_graphs):
        """Pushback 7-A — eager validation walks intergraph_edges."""
        f = mg_with_two_graphs
        # Add an edge first.
        f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "EVOKES",
        )
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(IntergraphEdgeType(name="EVOKES"))
        f["mg"].attach_schema(ms, schema_name="ms1")
        assert f["mg"].schema_name == "ms1"

    def test_returns_schema_for_chaining(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ms = MetagraphSchema()
        result = f["mg"].attach_schema(ms, schema_name="ms")
        assert result is ms


class TestAttachSchemaEagerValidation:
    def test_existing_edge_violates_type_existence(self, mg_with_two_graphs):
        """Pushback 7-A — first violation raises; state unchanged."""
        f = mg_with_two_graphs
        f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "EVOKES",
        )
        ms = MetagraphSchema()
        # No EVOKES type registered.
        with pytest.raises(UnknownTypeError):
            f["mg"].attach_schema(ms, schema_name="ms1")
        # Pushback 29-A — state unchanged on raise.
        assert f["mg"].schema_name is None
        assert f["mg"].schema is None

    def test_existing_edge_violates_role_constraint(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "EVOKES",
        )
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="EVOKES",
                allowed_source_graphs=frozenset({"WRONG_ROLE"}),
            )
        )
        with pytest.raises(UnknownTypeError):
            f["mg"].attach_schema(ms, schema_name="ms1")
        assert f["mg"].schema_name is None

    def test_existing_edge_violates_strict_property_typing(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "EVOKES",
            properties={"weight": "not-a-float"},
        )
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="EVOKES",
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        with pytest.raises(PropertyShapeError):
            f["mg"].attach_schema(ms, schema_name="ms1")
        assert f["mg"].schema_name is None

    def test_metaedges_skipped_in_05b(self, mg_with_two_graphs):
        """Pushback 9-A — metaedges/metahyperedges NOT validated in 05b."""
        f = mg_with_two_graphs
        # Add a metaedge with arbitrary type_name.
        f["mg"].add_metaedge(
            f["g_lex"].graph_id, f["g_cpt"].graph_id, "ARBITRARY_META_TYPE",
        )
        f["mg"].add_metahyperedge(
            [f["g_lex"].graph_id, f["g_cpt"].graph_id],
            type_name="ARBITRARY_MHE_TYPE",
        )
        # Schema has NO MetaEdgeType / MetaHyperEdgeType (per Pushback 1-C
        # those land in 05c). Attach succeeds — metaedges are not
        # validated in 05b.
        ms = MetagraphSchema()
        f["mg"].attach_schema(ms, schema_name="ms1")
        assert f["mg"].schema_name == "ms1"


class TestAttachSchemaOneAtMost:
    def test_attach_while_attached_refuses(self, mg_with_two_graphs):
        """Pushback 12-A — attach while different schema attached refuses."""
        f = mg_with_two_graphs
        ms1 = MetagraphSchema()
        ms2 = MetagraphSchema()
        f["mg"].attach_schema(ms1, schema_name="ms1")
        with pytest.raises(IdentityError) as exc:
            f["mg"].attach_schema(ms2, schema_name="ms2")
        assert "detach" in str(exc.value).lower()

    def test_re_attach_same_schema_runs_fresh_validation(self, mg_with_two_graphs):
        """Pushback 32-D — re-attach with same name is fresh validation.

        The semantic under test: even when ``schema_name`` matches the
        currently-attached value, ``attach_schema`` re-runs the full
        eager validation walk. This surfaces drift from schema mutation
        between attaches (the Pushback 23-A footgun).

        Flow:
          1. Empty schema; attach (validates 0 edges).
          2. Detach.
          3. Add an edge with arbitrary type (no schema → no validation).
          4. Re-attach same empty schema → eager validation refuses
             because the edge's type_name is not in the empty vocab.
        """
        f = mg_with_two_graphs
        ms = MetagraphSchema()
        # Step 1: attach empty schema (succeeds; nothing to validate).
        f["mg"].attach_schema(ms, schema_name="ms1")
        # Step 2: detach.
        previous = f["mg"].detach_schema()
        assert previous == "ms1"
        # Step 3: add edge with arbitrary type (no schema attached).
        f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "ARBITRARY",
        )
        # Step 4: re-attach SAME schema by name (vocab is still empty).
        # Pushback 32-D: re-attach is fresh validation, not silent
        # no-op — ARBITRARY is not in the empty vocab → refuse.
        with pytest.raises(UnknownTypeError):
            f["mg"].attach_schema(ms, schema_name="ms1")
        # Pushback 29-A — atomic refusal: state unchanged.
        assert f["mg"].schema_name is None
        assert f["mg"].schema is None


class TestDetachSchema:
    def test_detach_clears_state(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ms = MetagraphSchema()
        f["mg"].attach_schema(ms, schema_name="ms1")
        previous = f["mg"].detach_schema()
        assert previous == "ms1"
        assert f["mg"].schema_name is None
        assert f["mg"].schema is None

    def test_detach_when_none_returns_none(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        previous = f["mg"].detach_schema()
        assert previous is None

    def test_detach_non_destructive(self, mg_with_two_graphs):
        """Pushback 26-A — detach is non-destructive; intergraph_edges unchanged."""
        f = mg_with_two_graphs
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(IntergraphEdgeType(name="EVOKES"))
        f["mg"].attach_schema(ms, schema_name="ms1")
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "EVOKES",
        )
        f["mg"].detach_schema()
        # Edge remains unchanged.
        assert ie.edge_id in f["mg"].intergraph_edges
        assert f["mg"].intergraph_edges[ie.edge_id].type_name == "EVOKES"


class TestAddIntergraphEdgeWithSchemaAttached:
    def test_unknown_type_raises(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ms = MetagraphSchema()
        # No types registered.
        f["mg"].attach_schema(ms, schema_name="ms")
        with pytest.raises(UnknownTypeError):
            f["mg"].add_intergraph_edge(
                f["g_lex"].graph_id, f["n_lex"].node_id,
                f["g_cpt"].graph_id, f["n_cpt"].node_id, "ANY_TYPE",
            )

    def test_role_constraint_violation(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="EVOKES",
                allowed_source_graphs=frozenset({"wrong_role"}),
            )
        )
        f["mg"].attach_schema(ms, schema_name="ms")
        with pytest.raises(UnknownTypeError):
            f["mg"].add_intergraph_edge(
                f["g_lex"].graph_id, f["n_lex"].node_id,
                f["g_cpt"].graph_id, f["n_cpt"].node_id, "EVOKES",
            )

    def test_strict_property_violation(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="EVOKES",
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        f["mg"].attach_schema(ms, schema_name="ms")
        with pytest.raises(PropertyShapeError):
            f["mg"].add_intergraph_edge(
                f["g_lex"].graph_id, f["n_lex"].node_id,
                f["g_cpt"].graph_id, f["n_cpt"].node_id, "EVOKES",
                properties={"weight": "not-a-float"},
            )

    def test_happy_path_with_strict_schema(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ms = MetagraphSchema(strict=True)
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="EVOKES",
                allowed_source_types=frozenset({"Word"}),
                allowed_target_types=frozenset({"Concept"}),
                allowed_source_graphs=frozenset({"lexicon"}),
                allowed_target_graphs=frozenset({"concepts"}),
                property_types={"weight": PropertyType.FLOAT},
            )
        )
        f["mg"].attach_schema(ms, schema_name="ms")
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "EVOKES",
            properties={"weight": 0.5},
        )
        assert ie.edge_id in f["mg"].intergraph_edges


class TestSchemaReuseAcrossMetagraphs:
    def test_one_schema_multiple_metagraphs(self):
        """Pushback 11-A — schemas reusable across N metagraphs."""
        ms = MetagraphSchema()
        ms.add_intergraph_edge_type(
            IntergraphEdgeType(
                name="EVOKES",
                allowed_source_graphs=frozenset({"lexicon"}),
                allowed_target_graphs=frozenset({"concepts"}),
            )
        )

        def _build_mg(name):
            mg = Metagraph(name=name)
            g_lex = Graph(name=f"{name}_lex", role="lexicon")
            g_cpt = Graph(name=f"{name}_cpt", role="concepts")
            mg.add_graph(g_lex)
            mg.add_graph(g_cpt)
            n_lex = g_lex.add_node("v1", type_name="Word")
            n_cpt = g_cpt.add_node("v2", type_name="Concept")
            return mg, g_lex, g_cpt, n_lex, n_cpt

        mg1_data = _build_mg("m1")
        mg2_data = _build_mg("m2")
        mg1_data[0].attach_schema(ms, schema_name="shared")
        mg2_data[0].attach_schema(ms, schema_name="shared")
        # Both metagraphs reference the same schema instance.
        assert mg1_data[0].schema is ms
        assert mg2_data[0].schema is ms
        # Adding an edge in each works.
        mg1_data[0].add_intergraph_edge(
            mg1_data[1].graph_id, mg1_data[3].node_id,
            mg1_data[2].graph_id, mg1_data[4].node_id, "EVOKES",
        )
        mg2_data[0].add_intergraph_edge(
            mg2_data[1].graph_id, mg2_data[3].node_id,
            mg2_data[2].graph_id, mg2_data[4].node_id, "EVOKES",
        )


class TestEmptyVocabSchemaAttachStrict:
    """Pushback 24-hybrid — empty vocab + strict."""
    def test_attach_to_metagraph_with_existing_edges_strict_refuses(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "EVOKES",
        )
        ms = MetagraphSchema(strict=True)  # empty vocab
        # Strict + no EVOKES type → require_intergraph_edge_type raises
        # at attach-time eager walk.
        with pytest.raises(UnknownTypeError):
            f["mg"].attach_schema(ms, schema_name="empty_strict")

    def test_attach_to_metagraph_with_no_edges_succeeds(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ms = MetagraphSchema(strict=True)
        # Empty schema + no edges = nothing to validate. Succeeds.
        f["mg"].attach_schema(ms, schema_name="empty_strict")
        assert f["mg"].schema_name == "empty_strict"
