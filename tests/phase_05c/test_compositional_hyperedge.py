"""Phase 05c — compositional flag on IntergraphHyperEdge + cascade refusal."""

from __future__ import annotations

import pytest

from mindsos_core import (
    CompositionalImmutableError,
    Graph,
    IntergraphHyperEdge,
    IntergraphHyperEdgeType,
    Metagraph,
    MetagraphSchema,
)


class TestCompositionalImmutability:
    def test_compositional_flag_immutable_post_create(self):
        ihe = IntergraphHyperEdge(
            anchors=(("g1", "n1"),),
            members=(("g2", "n2"), ("g2", "n3")),
            type_name="T",
            compositional=True,
        )
        with pytest.raises(CompositionalImmutableError):
            ihe.compositional = False

    def test_compositional_default_false(self):
        ihe = IntergraphHyperEdge(
            anchors=(("g1", "n1"),),
            members=(("g2", "n2"), ("g2", "n3")),
            type_name="T",
        )
        assert ihe.compositional is False


class TestRemoveRefusal:
    def test_remove_compositional_refused(self):
        mg = Metagraph(name="m")
        g_w = Graph(name="word", role="word")
        g_l = Graph(name="letter", role="letter")
        mg.add_graph(g_w)
        mg.add_graph(g_l)
        g_w.add_node("cat", type_name="Word", node_id="cat")
        g_l.add_node("c", type_name="Letter", node_id="c")
        g_l.add_node("a", type_name="Letter", node_id="a")
        ihe = mg.add_intergraph_hyperedge(
            anchors=[(g_w.graph_id, "cat")],
            members=[(g_l.graph_id, "c"), (g_l.graph_id, "a")],
            type_name="COMPOSED_OF",
            compositional=True,
        )
        with pytest.raises(CompositionalImmutableError):
            mg.remove_intergraph_hyperedge(ihe.edge_id)
        # State unchanged.
        assert ihe.edge_id in mg.intergraph_hyperedges

    def test_remove_non_compositional_succeeds(self):
        mg = Metagraph(name="m")
        g_w = Graph(name="word", role="word")
        g_l = Graph(name="letter", role="letter")
        mg.add_graph(g_w)
        mg.add_graph(g_l)
        g_w.add_node("cat", type_name="Word", node_id="cat")
        g_l.add_node("c", type_name="Letter", node_id="c")
        g_l.add_node("a", type_name="Letter", node_id="a")
        ihe = mg.add_intergraph_hyperedge(
            anchors=[(g_w.graph_id, "cat")],
            members=[(g_l.graph_id, "c"), (g_l.graph_id, "a")],
            type_name="COMPOSED_OF",
            compositional=False,
        )
        mg.remove_intergraph_hyperedge(ihe.edge_id)
        assert ihe.edge_id not in mg.intergraph_hyperedges


class TestUpdateRefusalOnCompositional:
    def test_update_refused(self):
        mg = Metagraph(name="m")
        g_w = Graph(name="word", role="word")
        g_l = Graph(name="letter", role="letter")
        mg.add_graph(g_w)
        mg.add_graph(g_l)
        g_w.add_node("cat", type_name="Word", node_id="cat")
        g_l.add_node("c", type_name="Letter", node_id="c")
        g_l.add_node("a", type_name="Letter", node_id="a")
        ihe = mg.add_intergraph_hyperedge(
            anchors=[(g_w.graph_id, "cat")],
            members=[(g_l.graph_id, "c"), (g_l.graph_id, "a")],
            type_name="COMPOSED_OF",
            compositional=True,
        )
        with pytest.raises(CompositionalImmutableError):
            mg.update_intergraph_hyperedge(
                ihe.edge_id, properties={"k": "v"},
            )


class TestRemoveGraphCascadeRefusal:
    """P17-A extended for 05c — atomic precheck across BOTH edge variants."""

    def _build_mg(self):
        mg = Metagraph(name="m")
        g_w = Graph(name="word", role="word")
        g_l = Graph(name="letter", role="letter")
        mg.add_graph(g_w)
        mg.add_graph(g_l)
        g_w.add_node("cat", type_name="Word", node_id="cat")
        g_l.add_node("c", type_name="Letter", node_id="c")
        g_l.add_node("a", type_name="Letter", node_id="a")
        return mg, g_w, g_l

    def test_remove_graph_anchor_side_refused(self):
        mg, g_w, g_l = self._build_mg()
        mg.add_intergraph_hyperedge(
            anchors=[(g_w.graph_id, "cat")],
            members=[(g_l.graph_id, "c"), (g_l.graph_id, "a")],
            type_name="COMPOSED_OF",
            compositional=True,
        )
        with pytest.raises(
            CompositionalImmutableError,
            match="anchor side",
        ):
            mg.remove_graph(g_w.graph_id)
        # State unchanged.
        assert g_w.graph_id in mg.graphs

    def test_remove_graph_member_side_refused(self):
        mg, g_w, g_l = self._build_mg()
        mg.add_intergraph_hyperedge(
            anchors=[(g_w.graph_id, "cat")],
            members=[(g_l.graph_id, "c"), (g_l.graph_id, "a")],
            type_name="COMPOSED_OF",
            compositional=True,
        )
        with pytest.raises(
            CompositionalImmutableError,
            match="member side",
        ):
            mg.remove_graph(g_l.graph_id)
        assert g_l.graph_id in mg.graphs

    def test_remove_graph_non_compositional_cascades(self):
        # Non-compositional incident hyperedge cascades cleanly.
        mg, g_w, g_l = self._build_mg()
        ihe = mg.add_intergraph_hyperedge(
            anchors=[(g_w.graph_id, "cat")],
            members=[(g_l.graph_id, "c"), (g_l.graph_id, "a")],
            type_name="COMPOSED_OF",
            compositional=False,
        )
        # Remove the letter graph — non-compositional cascade succeeds.
        mg.remove_graph(g_l.graph_id)
        assert g_l.graph_id not in mg.graphs
        assert ihe.edge_id not in mg.intergraph_hyperedges

    def test_error_message_includes_edge_kind(self):
        mg, g_w, g_l = self._build_mg()
        mg.add_intergraph_hyperedge(
            anchors=[(g_w.graph_id, "cat")],
            members=[(g_l.graph_id, "c"), (g_l.graph_id, "a")],
            type_name="COMPOSED_OF",
            compositional=True,
        )
        with pytest.raises(CompositionalImmutableError) as exc_info:
            mg.remove_graph(g_w.graph_id)
        # P17-A extended — error message names edge_kind.
        assert "intergraph_hyperedge" in str(exc_info.value)
