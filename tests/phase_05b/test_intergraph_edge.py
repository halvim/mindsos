"""IntergraphEdge dataclass + factory + cardinality + node-existence tests.

Covers Pushbacks 2-A (compositional top-level field), 13-A (single
node-existence check), 14-A (mint via mg.mint_id), 16-A (validation
order), 22-A (compositional immutability via __setattr__).
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    CompositionalImmutableError,
    CypherError,
    Graph,
    IdentityError,
    IntergraphEdge,
    Metagraph,
    PropertyShapeError,
    SchemaError,
)


class TestIntergraphEdgeDataclass:
    def test_kw_only_construction(self):
        ie = IntergraphEdge(
            source_graph_id="g1",
            source_node_id="n1",
            target_graph_id="g2",
            target_node_id="n2",
            type_name="EVOKES",
        )
        assert ie.source_graph_id == "g1"
        assert ie.source_node_id == "n1"
        assert ie.target_graph_id == "g2"
        assert ie.target_node_id == "n2"
        assert ie.type_name == "EVOKES"
        assert ie.compositional is False
        assert ie.label is None
        assert ie.properties == {}
        assert isinstance(ie.edge_id, str) and len(ie.edge_id) > 0

    def test_post_init_cypher_regex_enforced(self):
        with pytest.raises(CypherError):
            IntergraphEdge(
                source_graph_id="g1",
                source_node_id="n1",
                target_graph_id="g2",
                target_node_id="n2",
                type_name="lowercase_invalid",
            )

    def test_compositional_default_false(self):
        ie = IntergraphEdge(
            source_graph_id="g1",
            source_node_id="n1",
            target_graph_id="g2",
            target_node_id="n2",
            type_name="X",
        )
        assert ie.compositional is False

    def test_compositional_true_constructs(self):
        ie = IntergraphEdge(
            source_graph_id="g1",
            source_node_id="n1",
            target_graph_id="g2",
            target_node_id="n2",
            type_name="X",
            compositional=True,
        )
        assert ie.compositional is True

    def test_compositional_immutability_setattr_override(self):
        """Pushback 22-A — __setattr__ refuses re-assignment to compositional."""
        ie = IntergraphEdge(
            source_graph_id="g1",
            source_node_id="n1",
            target_graph_id="g2",
            target_node_id="n2",
            type_name="X",
            compositional=False,
        )
        with pytest.raises(CompositionalImmutableError):
            ie.compositional = True
        # Even setting it to its current value is refused (defensive).
        with pytest.raises(CompositionalImmutableError):
            ie.compositional = False

    def test_compositional_immutability_works_for_true_too(self):
        ie = IntergraphEdge(
            source_graph_id="g1",
            source_node_id="n1",
            target_graph_id="g2",
            target_node_id="n2",
            type_name="X",
            compositional=True,
        )
        with pytest.raises(CompositionalImmutableError):
            ie.compositional = False

    def test_other_field_mutation_works(self):
        """Only ``compositional`` is locked; label and properties mutate."""
        ie = IntergraphEdge(
            source_graph_id="g1",
            source_node_id="n1",
            target_graph_id="g2",
            target_node_id="n2",
            type_name="X",
        )
        ie.label = "renamed"
        assert ie.label == "renamed"
        ie.properties = {"k": "v"}
        assert ie.properties == {"k": "v"}

    def test_repr_compositional_marker(self):
        ie = IntergraphEdge(
            source_graph_id="g1",
            source_node_id="n1",
            target_graph_id="g2",
            target_node_id="n2",
            type_name="X",
            compositional=True,
        )
        assert "compositional" in repr(ie)

    def test_repr_no_marker_when_false(self):
        ie = IntergraphEdge(
            source_graph_id="g1",
            source_node_id="n1",
            target_graph_id="g2",
            target_node_id="n2",
            type_name="X",
        )
        assert "compositional" not in repr(ie)

    def test_eq_by_edge_id(self):
        ie1 = IntergraphEdge(
            source_graph_id="g1", source_node_id="n1",
            target_graph_id="g2", target_node_id="n2",
            type_name="X", edge_id="same",
        )
        ie2 = IntergraphEdge(
            source_graph_id="g1", source_node_id="n1",
            target_graph_id="g2", target_node_id="n2",
            type_name="DIFFERENT", edge_id="same",
        )
        assert ie1 == ie2  # eq by edge_id only.
        assert hash(ie1) == hash(ie2)


class TestAddIntergraphEdgeFactory:
    def test_happy_path(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id,
            "EVOKES",
        )
        assert ie.edge_id in f["mg"].intergraph_edges
        assert f["mg"].identity.contains(ie.edge_id)

    def test_step_1_source_graph_missing(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        with pytest.raises(IdentityError) as exc:
            f["mg"].add_intergraph_edge(
                "nonexistent", f["n_lex"].node_id,
                f["g_cpt"].graph_id, f["n_cpt"].node_id,
                "X",
            )
        assert "source graph" in str(exc.value)

    def test_step_2_target_graph_missing(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        with pytest.raises(IdentityError) as exc:
            f["mg"].add_intergraph_edge(
                f["g_lex"].graph_id, f["n_lex"].node_id,
                "nonexistent", f["n_cpt"].node_id,
                "X",
            )
        assert "target graph" in str(exc.value)

    def test_step_3_same_graph_refused(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        with pytest.raises(SchemaError) as exc:
            f["mg"].add_intergraph_edge(
                f["g_lex"].graph_id, f["n_lex"].node_id,
                f["g_lex"].graph_id, f["n_lex"].node_id,
                "X",
            )
        assert "different" in str(exc.value).lower()

    def test_step_4_source_node_missing(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        with pytest.raises(IdentityError) as exc:
            f["mg"].add_intergraph_edge(
                f["g_lex"].graph_id, "nonexistent",
                f["g_cpt"].graph_id, f["n_cpt"].node_id,
                "X",
            )
        assert "source node" in str(exc.value)

    def test_step_5_target_node_missing(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        with pytest.raises(IdentityError) as exc:
            f["mg"].add_intergraph_edge(
                f["g_lex"].graph_id, f["n_lex"].node_id,
                f["g_cpt"].graph_id, "nonexistent",
                "X",
            )
        assert "target node" in str(exc.value)

    def test_step_6_invalid_cypher_type(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        with pytest.raises(CypherError):
            f["mg"].add_intergraph_edge(
                f["g_lex"].graph_id, f["n_lex"].node_id,
                f["g_cpt"].graph_id, f["n_cpt"].node_id,
                "lowercase_bad",
            )

    def test_step_7_reserved_property_key(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        with pytest.raises(PropertyShapeError):
            f["mg"].add_intergraph_edge(
                f["g_lex"].graph_id, f["n_lex"].node_id,
                f["g_cpt"].graph_id, f["n_cpt"].node_id,
                "X",
                properties={"_compositional": True},
            )

    def test_step_7_reserved_intergraph_edges_key(self, mg_with_two_graphs):
        """Pushback 18-A — `intergraph_edges` reserved at user-property scope."""
        f = mg_with_two_graphs
        with pytest.raises(PropertyShapeError):
            f["mg"].add_intergraph_edge(
                f["g_lex"].graph_id, f["n_lex"].node_id,
                f["g_cpt"].graph_id, f["n_cpt"].node_id,
                "X",
                properties={"intergraph_edges": "bad"},
            )

    def test_step_7_reserved_schema_name_key(self, mg_with_two_graphs):
        """Pushback 18-A — `schema_name` reserved at user-property scope."""
        f = mg_with_two_graphs
        with pytest.raises(PropertyShapeError):
            f["mg"].add_intergraph_edge(
                f["g_lex"].graph_id, f["n_lex"].node_id,
                f["g_cpt"].graph_id, f["n_cpt"].node_id,
                "X",
                properties={"schema_name": "bad"},
            )

    def test_step_11_explicit_edge_id_used(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id,
            "X",
            edge_id="my-explicit-id",
        )
        assert ie.edge_id == "my-explicit-id"

    def test_step_13_id_collision_in_registry(self, mg_with_two_graphs):
        """If supplied edge_id collides with an existing registered id, refuse."""
        f = mg_with_two_graphs
        f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id,
            "X", edge_id="dupe",
        )
        with pytest.raises(IdentityError):
            f["mg"].add_intergraph_edge(
                f["g_lex"].graph_id, f["n_lex"].node_id,
                f["g_cpt"].graph_id, f["n_cpt"].node_id,
                "Y", edge_id="dupe",
            )

    def test_compositional_construction(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id,
            "COMPOSED_OF", compositional=True,
        )
        assert ie.compositional is True

    def test_label_round_trip(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id,
            "X", label="my label",
        )
        assert ie.label == "my label"

    def test_properties_round_trip(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id,
            "X", properties={"weight": 0.42, "tag": "primary"},
        )
        assert ie.properties == {"weight": 0.42, "tag": "primary"}

    def test_edge_registered_in_identity(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id,
            "X",
        )
        assert ie.edge_id in f["mg"].identity.ids

    def test_added_to_intergraph_edges_dict(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id,
            "X",
        )
        assert f["mg"].intergraph_edges[ie.edge_id] is ie


class TestRemoveIntergraphEdge:
    def test_happy_path(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
        )
        f["mg"].remove_intergraph_edge(ie.edge_id)
        assert ie.edge_id not in f["mg"].intergraph_edges
        assert not f["mg"].identity.contains(ie.edge_id)

    def test_unknown_id_raises(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        with pytest.raises(IdentityError):
            f["mg"].remove_intergraph_edge("nonexistent")

    def test_compositional_refuses(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id,
            "X", compositional=True,
        )
        with pytest.raises(CompositionalImmutableError):
            f["mg"].remove_intergraph_edge(ie.edge_id)
        # Edge remains.
        assert ie.edge_id in f["mg"].intergraph_edges


class TestUpdateIntergraphEdgeProperties:
    def test_merge_default(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            properties={"a": 1},
        )
        f["mg"].update_intergraph_edge_properties(ie.edge_id, {"b": 2})
        assert ie.properties == {"a": 1, "b": 2}

    def test_replace_swaps(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            properties={"a": 1},
        )
        f["mg"].update_intergraph_edge_properties(
            ie.edge_id, {"b": 2}, replace=True,
        )
        assert ie.properties == {"b": 2}

    def test_compositional_refuses(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            compositional=True,
        )
        with pytest.raises(CompositionalImmutableError):
            f["mg"].update_intergraph_edge_properties(
                ie.edge_id, {"k": "v"},
            )

    def test_unknown_id_raises(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        with pytest.raises(IdentityError):
            f["mg"].update_intergraph_edge_properties(
                "nonexistent", {"k": "v"},
            )

    def test_property_shape_error(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
        )
        with pytest.raises(PropertyShapeError):
            f["mg"].update_intergraph_edge_properties(
                ie.edge_id, {"_compositional": True},
            )


class TestIterIntergraphEdges:
    def test_empty(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        assert list(f["mg"].iter_intergraph_edges()) == []

    def test_with_edges(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie1 = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
        )
        ie2 = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "Y",
        )
        edges = list(f["mg"].iter_intergraph_edges())
        assert len(edges) == 2
        assert {ie1.edge_id, ie2.edge_id} == {e.edge_id for e in edges}
