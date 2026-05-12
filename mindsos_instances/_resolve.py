"""Endpoint-resolution helpers for materialise (round-7 P58 A).

Edge / HyperEdge / MetaEdge / MetaHyperEdge instances can carry
ID-overrides (``source_id``, ``target_id``, ``member_ids``,
``source_graph_id``, ``target_graph_id``, ``graph_ids``). Materialise
must produce a fresh Core object — but the Core dataclasses require
object refs (``Edge.source: Node``, ``HyperEdge.nodes: Set[Node]``),
not ID strings. This module walks the metagraph to resolve override IDs
into the underlying Core objects.

Per round-7 P58 A pick: ``Metagraph`` has no reverse-index from node-id
→ owning Graph; resolution walks ``metagraph.graphs.values()`` O(G×N).
Phase 06 single-call-demo scope absorbs the cost; Phase 07 persistence
can add an indexed lookup if profile shows hotness.
"""

from __future__ import annotations

from typing import Iterable, Set

from mindsos_core import Graph, Metagraph, Node
from mindsos_core.exceptions import IdentityError


def resolve_node(metagraph: Metagraph, node_id: str) -> Node:
    """Find the :class:`Node` with ``node_id`` in any contained Graph.

    Raises :class:`IdentityError` if no contained Graph holds that
    node id. O(G) lookup, O(1) per Graph (dict access).
    """
    for graph in metagraph.graphs.values():
        if node_id in graph.nodes:
            return graph.nodes[node_id]
    raise IdentityError(
        f"resolve_node: no Node with id {node_id!r} in any contained "
        f"graph of metagraph {metagraph.metagraph_id!r}."
    )


def resolve_nodes(
    metagraph: Metagraph, node_ids: Iterable[str]
) -> Set[Node]:
    """Resolve a set of node ids to a set of Node objects."""
    return {resolve_node(metagraph, nid) for nid in node_ids}


def resolve_graph(metagraph: Metagraph, graph_id: str) -> Graph:
    """Resolve a graph_id to the contained Graph."""
    if graph_id not in metagraph.graphs:
        raise IdentityError(
            f"resolve_graph: graph_id {graph_id!r} not in metagraph "
            f"{metagraph.metagraph_id!r}."
        )
    return metagraph.graphs[graph_id]
