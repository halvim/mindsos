"""Compositional flag + remove_graph cascade precheck tests.

Pushbacks 6-A (no escape hatch), 17-A (atomic precheck), 22-A
(__setattr__ immutability).
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    CompositionalImmutableError,
    IdentityError,
    Metagraph,
)


class TestCompositionalImmutability:
    def test_factory_accepts_compositional_true(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            compositional=True,
        )
        assert ie.compositional is True

    def test_remove_intergraph_edge_refuses_compositional(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            compositional=True,
        )
        with pytest.raises(CompositionalImmutableError) as exc:
            f["mg"].remove_intergraph_edge(ie.edge_id)
        assert "compositional" in str(exc.value).lower()
        # Edge survives.
        assert ie.edge_id in f["mg"].intergraph_edges

    def test_update_properties_refuses_compositional(self, mg_with_two_graphs):
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

    def test_setattr_override_refuses_post_init(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            compositional=False,
        )
        # Pushback 22-A — flip refused.
        with pytest.raises(CompositionalImmutableError):
            ie.compositional = True


class TestRemoveGraphCascadeAtomicPrecheck:
    def test_no_compositional_normal_cascade(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
        )
        f["mg"].remove_graph(f["g_lex"].graph_id)
        # Edge cascaded out.
        assert ie.edge_id not in f["mg"].intergraph_edges
        assert f["g_lex"].graph_id not in f["mg"].graphs

    def test_compositional_incident_blocks_remove_graph(self, mg_with_two_graphs):
        """Pushback 17-A — atomic precheck refuses; state unchanged."""
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            compositional=True,
        )
        with pytest.raises(CompositionalImmutableError) as exc:
            f["mg"].remove_graph(f["g_lex"].graph_id)
        # Pushback 17-A — state unchanged.
        assert f["g_lex"].graph_id in f["mg"].graphs
        assert ie.edge_id in f["mg"].intergraph_edges
        # Error message names the offending edge_id.
        assert ie.edge_id in str(exc.value)

    def test_compositional_target_side_also_blocks(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            compositional=True,
        )
        # Removing the TARGET graph also blocks.
        with pytest.raises(CompositionalImmutableError):
            f["mg"].remove_graph(f["g_cpt"].graph_id)

    def test_mixed_compositional_and_normal_atomic_refusal(self, mg_with_two_graphs):
        """Atomic precheck: any compositional incident → no mutation at all."""
        f = mg_with_two_graphs
        # Add a non-compositional edge first.
        ie_normal = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "NORMAL",
        )
        ie_compositional = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "COMPOSED_OF",
            compositional=True,
        )
        with pytest.raises(CompositionalImmutableError):
            f["mg"].remove_graph(f["g_lex"].graph_id)
        # BOTH edges remain (atomic).
        assert ie_normal.edge_id in f["mg"].intergraph_edges
        assert ie_compositional.edge_id in f["mg"].intergraph_edges
        # Graph remains.
        assert f["g_lex"].graph_id in f["mg"].graphs

    def test_unrelated_graph_removable_with_compositional_elsewhere(self, mg_with_two_graphs):
        """Compositional edges on other graphs don't block unrelated removals."""
        f = mg_with_two_graphs
        # Add a third graph not incident to the compositional edge.
        from mindsos_core import Graph
        g3 = Graph(name="orth", role="orthography")
        f["mg"].add_graph(g3)
        # Compositional edge between g_lex and g_cpt.
        f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            compositional=True,
        )
        # Removing g3 (no incident edges) should succeed.
        f["mg"].remove_graph(g3.graph_id)
        assert g3.graph_id not in f["mg"].graphs

    def test_unknown_graph_id_raises(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        with pytest.raises(IdentityError):
            f["mg"].remove_graph("nonexistent")


class TestR38NodeRemovalRespectsComposition:
    """R38 — the identity contract, enforced one level below where it was.

    ``remove_graph`` prechecks incident compositional edges and
    ``remove_intergraph_edge`` refuses on the flag, but ``Graph.remove_node``
    is graph-level and a Graph holds no reference to its metagraph — so a
    probe removed a node carrying four compositional edges and left seven
    edges pointing at a node that no longer existed. The metagraph now
    subscribes to the Graph remove-observer seam for the graphs it contains.
    """

    def test_compositional_edge_blocks_removing_the_node_it_rests_on(
        self, mg_with_two_graphs
    ):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            compositional=True,
        )
        with pytest.raises(CompositionalImmutableError) as exc:
            f["g_lex"].remove_node(f["n_lex"].node_id)
        # Precheck-style: nothing moved.
        assert f["n_lex"].node_id in f["g_lex"].nodes
        assert ie.edge_id in f["mg"].intergraph_edges
        # The message names the edge, as remove_graph's does.
        assert ie.edge_id in str(exc.value)
        assert "source" in str(exc.value)

    def test_the_target_side_blocks_too(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            compositional=True,
        )
        with pytest.raises(CompositionalImmutableError) as exc:
            f["g_cpt"].remove_node(f["n_cpt"].node_id)
        assert "target" in str(exc.value)
        assert f["n_cpt"].node_id in f["g_cpt"].nodes

    def test_a_NON_compositional_edge_does_not_block_the_node(
        self, mg_with_two_graphs
    ):
        """The guard is the composition's, not every intergraph edge's."""
        f = mg_with_two_graphs
        f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
        )
        f["g_lex"].remove_node(f["n_lex"].node_id)
        assert f["n_lex"].node_id not in f["g_lex"].nodes

    def test_an_unrelated_node_in_the_same_graph_still_removes(
        self, mg_with_two_graphs
    ):
        """⚠ The guard answers for ONE node, never for the graph."""
        f = mg_with_two_graphs
        f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            compositional=True,
        )
        other = f["g_lex"].add_node("dog", type_name="Word")
        f["g_lex"].remove_node(other.node_id)
        assert other.node_id not in f["g_lex"].nodes
        assert f["n_lex"].node_id in f["g_lex"].nodes

    def test_a_compositional_HYPEREDGE_blocks_both_of_its_sides(
        self, mg_with_two_graphs
    ):
        """⚠ **The same rule as remove_graph, including the member side.**
        A narrower rule here would mean the guarantee changed with the level,
        which is the class of defect R38 is."""
        f = mg_with_two_graphs
        # ⚠ A hyperedge may not be 1-to-1 — that is what IntergraphEdge is
        # for — so the member side carries two.
        second = f["g_cpt"].add_node("Cat#2", type_name="Concept")
        f["mg"].add_intergraph_hyperedge(
            anchors=[(f["g_lex"].graph_id, f["n_lex"].node_id)],
            members=[(f["g_cpt"].graph_id, f["n_cpt"].node_id),
                     (f["g_cpt"].graph_id, second.node_id)],
            type_name="COMPOSED_OF",
            compositional=True,
        )
        with pytest.raises(CompositionalImmutableError) as anchor_side:
            f["g_lex"].remove_node(f["n_lex"].node_id)
        assert "anchor" in str(anchor_side.value)
        with pytest.raises(CompositionalImmutableError) as member_side:
            f["g_cpt"].remove_node(f["n_cpt"].node_id)
        assert "member" in str(member_side.value)

    def test_the_guard_answers_for_NODES_and_not_for_intragraph_edges(
        self, mg_with_two_graphs
    ):
        """The seam dispatches node, edge and hyperedge removals through one
        callback carrying a bare id. An intragraph edge is not what a
        compositional IntergraphEdge points at."""
        f = mg_with_two_graphs
        f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            compositional=True,
        )
        other = f["g_lex"].add_node("dog", type_name="Word")
        edge = f["g_lex"].add_edge(f["n_lex"], other, "NEAR")
        f["g_lex"].remove_edge(edge.edge_id)
        assert edge.edge_id not in f["g_lex"].edges
