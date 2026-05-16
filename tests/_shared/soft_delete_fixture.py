"""Soft-delete integration fixture for Phase 10 (RR-13).

Phase 10 integration tests need a :class:`Metagraph` populated with
ALL 5 soft-deletable element kinds (Edge / HyperEdge / MetaEdge /
MetaHyperEdge / XRef) so a single fixture call exercises every
setter quartet + the persist drain + the WAL replayer dispatch.

Usage::

    from tests._shared.soft_delete_fixture import make_metagraph_with_soft_delete

    def test_persist_drain_round_trip(falkor_client):
        mg, ids = make_metagraph_with_soft_delete()
        # mg.deprecate_metaedge(ids["metaedge"]) ... etc.
        MetagraphRepository(falkor_client).persist(mg)
        ...

The ``ids`` dict provides string id handles for each element kind so
tests can target setter calls without grovelling through ``mg.graphs``
to find the right edge_id.

Per Phase 10 PB-8 — fixture scale is ≤10 elements per kind. No stress
tier ships in Phase 10. Returned shape:

* 3 contained graphs (``ontology`` / ``lexicon`` / ``concepts``)
* 4 nodes total (2 in ``ontology``, 1 in ``lexicon``, 1 in ``concepts``)
* 1 Edge (ontology-internal)
* 1 HyperEdge (ontology-internal, 2 members)
* 1 MetaEdge (ontology → lexicon)
* 1 MetaHyperEdge (3-member: all 3 graphs)
* 1 XRef (source in ontology, soft target id)

Per RR-13 — function-scoped (not pytest fixture) so tests can build
multiple independent metagraphs in one test.
"""

from __future__ import annotations

from typing import Dict, Tuple

from mindsos_core import Graph, Metagraph


def make_metagraph_with_soft_delete() -> Tuple[Metagraph, Dict[str, str]]:
    """Build a Metagraph populated with all 5 soft-deletable element kinds.

    Returns ``(mg, ids)`` where ``ids`` maps element-kind strings to
    the corresponding id handles:

    * ``"edge"`` → ``Edge.edge_id`` (in graph "ontology")
    * ``"hyperedge"`` → ``HyperEdge.edge_id`` (in graph "ontology")
    * ``"metaedge"`` → ``MetaEdge.edge_id`` (ontology → lexicon)
    * ``"metahyperedge"`` → ``MetaHyperEdge.edge_id`` (3-member span)
    * ``"xref"`` → ``XRef.xref_id`` (soft cross-metagraph ref)

    Additional handles for graph + node access:

    * ``"graph_ont"`` / ``"graph_lex"`` / ``"graph_conc"`` — graph_ids
    * ``"node_a"`` / ``"node_b"`` — nodes in ontology graph (for Edge endpoints)
    """
    mg = Metagraph(name="phase10-soft-delete-test")

    g_ont = Graph(name="ontology", role="ontology")
    g_lex = Graph(name="lexicon", role="lexicon")
    g_conc = Graph(name="concepts", role="concepts")
    mg.add_graph(g_ont)
    mg.add_graph(g_lex)
    mg.add_graph(g_conc)

    n_a = g_ont.add_node(value="alice", type_name="Person")
    n_b = g_ont.add_node(value="bob", type_name="Person")
    g_lex.add_node(value="word-alice", type_name="Word")
    g_conc.add_node(value="concept-X", type_name="Concept")

    e = g_ont.add_edge(source=n_a, target=n_b, type_name="KNOWS")
    he = g_ont.add_hyperedge(nodes={n_a, n_b}, type_name="LINKS")

    me = mg.add_metaedge(
        source_graph_id=g_ont.graph_id,
        target_graph_id=g_lex.graph_id,
        type_name="ALIGNS",
    )
    mhe = mg.add_metahyperedge(
        graph_ids=[g_ont.graph_id, g_lex.graph_id, g_conc.graph_id],
        type_name="SPANS",
    )

    # Soft XRef (no target_metagraph passed → no write-time validation).
    xref = mg.add_xref(
        source_id=n_a.node_id,
        target_metagraph_id="other-mg-id",
        target_role="ontology",
        target_id="target-node-id",
        ref_type="SPECIALISES",
    )

    ids = {
        "edge": e.edge_id,
        "hyperedge": he.edge_id,
        "metaedge": me.edge_id,
        "metahyperedge": mhe.edge_id,
        "xref": xref.xref_id,
        "graph_ont": g_ont.graph_id,
        "graph_lex": g_lex.graph_id,
        "graph_conc": g_conc.graph_id,
        "node_a": n_a.node_id,
        "node_b": n_b.node_id,
    }
    return mg, ids


__all__ = ["make_metagraph_with_soft_delete"]
