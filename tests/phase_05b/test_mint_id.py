"""Metagraph.mint_id tests (Pushbacks 7 carry-forward + 14-A).

ADR-0131 helper landed in 05b for IntergraphEdge factory's id-minting
path. Default UUID4Strategy ignores kind/content; custom strategies use
both.
"""

from __future__ import annotations

import uuid

import pytest

from mindsos_core import (
    IRIPassthroughStrategy,
    Metagraph,
    UUID4Strategy,
    UUID5FromContentStrategy,
)


class TestMintIdUUID4:
    def test_default_strategy_returns_uuid4(self):
        mg = Metagraph(name="t")
        result = mg.mint_id("intergraph_edge")
        # Validates as UUID.
        u = uuid.UUID(result)
        assert u.version == 4

    def test_distinct_calls_distinct_ids(self):
        mg = Metagraph(name="t")
        ids = {mg.mint_id("intergraph_edge") for _ in range(20)}
        assert len(ids) == 20

    def test_kind_argument_ignored_by_uuid4(self):
        mg = Metagraph(name="t")
        # Different kinds produce different UUIDs (because UUID4 ignores
        # kind and just generates randomly).
        a = mg.mint_id("intergraph_edge")
        b = mg.mint_id("metaedge")
        assert a != b

    def test_content_argument_accepted_and_ignored(self):
        mg = Metagraph(name="t")
        # Content dict is the protocol; UUID4 ignores it.
        result = mg.mint_id("intergraph_edge", {"any": "content"})
        u = uuid.UUID(result)
        assert u.version == 4


class TestMintIdUUID5FromContent:
    def test_deterministic_for_same_kind_and_content(self):
        mg = Metagraph(name="t", id_strategy=UUID5FromContentStrategy())
        a = mg.mint_id("intergraph_edge", {"src": "g1.n1", "tgt": "g2.n2"})
        b = mg.mint_id("intergraph_edge", {"src": "g1.n1", "tgt": "g2.n2"})
        assert a == b

    def test_different_content_different_id(self):
        mg = Metagraph(name="t", id_strategy=UUID5FromContentStrategy())
        a = mg.mint_id("intergraph_edge", {"src": "x"})
        b = mg.mint_id("intergraph_edge", {"src": "y"})
        assert a != b

    def test_no_content_raises(self):
        from mindsos_core import IdentityError
        mg = Metagraph(name="t", id_strategy=UUID5FromContentStrategy())
        with pytest.raises(IdentityError):
            mg.mint_id("intergraph_edge")  # no content


class TestMintIdIRIPassthrough:
    def test_iri_in_content_passed_through(self):
        mg = Metagraph(name="t", id_strategy=IRIPassthroughStrategy())
        iri = "oewn-2024:synset:02086723-n"
        result = mg.mint_id("node", {"iri": iri})
        assert result == iri

    def test_no_iri_falls_back_to_uuid4(self):
        mg = Metagraph(name="t", id_strategy=IRIPassthroughStrategy())
        result = mg.mint_id("intergraph_edge")
        # Falls back to UUID4 (default fallback).
        u = uuid.UUID(result)
        assert u.version == 4


class TestIntergraphEdgeFactoryUsesMintId:
    """Pushback 14-A — IntergraphEdge factory uniformly uses mg.mint_id."""

    def test_default_uuid4_assigned(self, mg_with_two_graphs):
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
        )
        u = uuid.UUID(ie.edge_id)
        assert u.version == 4

    def test_custom_strategy_used(self):
        from mindsos_core import Graph
        mg = Metagraph(name="t", id_strategy=UUID5FromContentStrategy())
        g1 = Graph(name="g1")
        g2 = Graph(name="g2")
        mg.add_graph(g1)
        mg.add_graph(g2)
        n1 = g1.add_node("v1", type_name="N")
        n2 = g2.add_node("v2", type_name="N")
        # The factory mints via mg.mint_id — UUID5 strategy raises if
        # content is None. The current factory doesn't pass content
        # (it just calls mg.mint_id("intergraph_edge")), so this raises.
        # That's the spec — custom strategies needing content must
        # extend the factory call site.
        from mindsos_core import IdentityError
        with pytest.raises(IdentityError):
            mg.add_intergraph_edge(
                g1.graph_id, n1.node_id, g2.graph_id, n2.node_id, "X",
            )

    def test_explicit_edge_id_skips_minting(self, mg_with_two_graphs):
        """Caller-supplied edge_id bypasses mint_id."""
        f = mg_with_two_graphs
        ie = f["mg"].add_intergraph_edge(
            f["g_lex"].graph_id, f["n_lex"].node_id,
            f["g_cpt"].graph_id, f["n_cpt"].node_id, "X",
            edge_id="explicit-id",
        )
        assert ie.edge_id == "explicit-id"
