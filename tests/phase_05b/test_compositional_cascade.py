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
