"""RPB-13 B — InMemoryClient unit assertions for iter_load_graph Cypher shape."""

from __future__ import annotations

import pytest

from mindsos_core.persistence import InMemoryClient
from mindsos_core.reconstruction import iter_load_graph


def test_iter_load_graph_rejects_zero_or_negative_batch_size() -> None:
    c = InMemoryClient()
    with pytest.raises(ValueError, match="batch_size"):
        list(iter_load_graph(c, "g1", batch_size=0))
    with pytest.raises(ValueError, match="batch_size"):
        list(iter_load_graph(c, "g1", batch_size=-1))


def test_iter_load_graph_emits_anchor_then_node_pages_then_trailer_queries() -> None:
    """The Cypher emit sequence: anchor → node_page* → edges → hyperedges → leak scan."""
    c = InMemoryClient()
    # Anchor.
    c.script([{"name": "g1", "role": "lex", "version": 1, "metagraph_id": None}])
    # Node page 1 (full — 2 nodes; batch_size=2 triggers another empty fetch).
    c.script([
        {"id": "n1", "type_name": "T", "value": "v1", "version": 1, "props": {}},
        {"id": "n2", "type_name": "T", "value": "v2", "version": 1, "props": {}},
    ])
    # Node page 2 (empty — termination).
    c.script([])
    # Trailer edges + hyperedges + leak scan.
    c.script([])
    c.script([])
    c.script([])

    batches = list(iter_load_graph(c, "g1", batch_size=2))
    assert len(batches) >= 1
    # The last batch contains the full assembled graph.
    final = batches[-1]
    assert "n1" in final.nodes
    assert "n2" in final.nodes


def test_iter_load_graph_paginates_with_skip_limit() -> None:
    """Node page query uses ORDER BY n.id SKIP $offset LIMIT $limit."""
    c = InMemoryClient()
    c.script([{"name": "g1", "role": "lex", "version": 1, "metagraph_id": None}])
    c.script([])  # First page empty.
    c.script([])  # Trailer edges.
    c.script([])  # Trailer hyperedges.
    c.script([])  # Trailer leak scan.

    list(iter_load_graph(c, "g1", batch_size=100))
    # Inspect the recorded node-page Cypher (2nd call after anchor).
    node_call = c.calls[1]
    query, params = node_call
    assert "ORDER BY n.id" in query
    assert "SKIP $offset" in query
    assert "LIMIT $limit" in query
    assert params.get("limit") == 100
    assert params.get("offset") == 0


def test_iter_load_graph_anchor_query_filters_by_gid() -> None:
    """Anchor query MATCHes :Graph {id: $gid}."""
    c = InMemoryClient()
    c.script([{"name": "g1", "role": "lex", "version": 1, "metagraph_id": None}])
    c.script([])
    c.script([])
    c.script([])
    c.script([])

    list(iter_load_graph(c, "graph-xyz", batch_size=10))
    anchor_call = c.calls[0]
    query, params = anchor_call
    assert "MATCH (g:Graph {id: $gid})" in query
    assert params.get("gid") == "graph-xyz"


def test_iter_load_graph_anchor_missing_raises_persistence_error() -> None:
    """No anchor row → :class:`PersistenceError`."""
    from mindsos_core.exceptions import PersistenceError

    c = InMemoryClient()
    c.script([])  # Empty anchor.
    with pytest.raises(PersistenceError, match="No :Graph row"):
        list(iter_load_graph(c, "ghost", batch_size=10))
