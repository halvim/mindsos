"""N-node :class:`Graph` fixture builder (Phase 08 RR-13 A).

Builds a connected synthetic :class:`Graph` with ``n_nodes`` nodes +
edges configurable via ``edge_density`` (default 1.5 = ~1.5 edges per
node). Used by:

* ``tests/phase_08/test_iter_load_graph_integration.py`` — RPB-1 A
  + RPB-8 A iter_load_graph cross-batch fidelity.
* ``tests/phase_08/test_iter_load_graph_10k.py`` — RPB-12 C opt-in
  10K-node streaming smoke test (``pytest.mark.slow``).
* Any Phase 08+ test needing a sized graph fixture.

Phase 08 PB-12 C — memory-budget assertion is structural
(``len(g.nodes) <= batch_size`` per yield); real memory-pressure
validation deferred to a future scale-test phase.
"""

from __future__ import annotations

from typing import Any


def make_large_graph_fixture(
    metagraph: Any,
    *,
    graph_name: str,
    role: str = "letters",
    n_nodes: int = 1_000,
    edge_density: float = 1.5,
) -> Any:
    """Construct a ``Graph`` with ``n_nodes`` nodes + (n_nodes * edge_density) edges.

    Node ids are deterministic strings ``node-<i>`` (zero-padded to keep
    id-order stable for ``ORDER BY n.id`` pagination tests). Edges
    connect each node to ``round(edge_density)`` later-id neighbours so
    a node-3 → node-23 cross-batch fidelity test (batch_size=10) has
    deterministic edge instances to assert against.

    Args:
        metagraph: The Phase 08 :class:`Metagraph` to attach the new
            Graph to. The function calls ``metagraph.add_graph(g)``.
        graph_name: New graph name (and base for node ids).
        role: Graph role (defaults to ``"letters"`` to match Phase 08
            recipe convention).
        n_nodes: Node count.
        edge_density: Average edges per node. Float allowed; rounded to
            int for the per-node neighbour count.

    Returns:
        The constructed :class:`Graph` (now attached to ``metagraph``).
    """
    # Local import — keeps the module loadable in sandboxes that don't
    # have mindsos_core on PYTHONPATH (parametrized tests gate the load).
    from mindsos_core.models.graph import Graph

    # Compute zero-pad width for stable lex-order across the dataset.
    pad = max(2, len(str(n_nodes - 1)))
    edges_per_node = max(0, int(round(edge_density)))

    g = Graph(
        name=graph_name,
        role=role,
        identity=metagraph.identity,
    )

    # Nodes — deterministic ids `node-<i>` in lex order.
    node_objs = []
    for i in range(n_nodes):
        nid = f"node-{i:0{pad}d}"
        node = g.add_node(
            value=i,
            type_name="LETTER",
            node_id=nid,
            _validate=False,
        )
        node_objs.append(node)

    # Edges — each node-i connects to node-(i + 10), node-(i + 20), ...
    # up to edges_per_node neighbours. The +10 offset keeps a node-3
    # → node-23 cross-batch edge (when batch_size=10) for the
    # RPB-8 A iii test.
    if edges_per_node > 0:
        edge_seq = 0
        for i, src in enumerate(node_objs):
            for k in range(1, edges_per_node + 1):
                j = i + 10 * k
                if j >= n_nodes:
                    break
                tgt = node_objs[j]
                eid = f"edge-{edge_seq:0{pad + 2}d}"
                g.add_edge(
                    source=src,
                    target=tgt,
                    type_name="NEIGHBOUR",
                    edge_id=eid,
                    _validate=False,
                )
                edge_seq += 1

    metagraph.add_graph(g)
    return g


__all__ = ["make_large_graph_fixture"]
