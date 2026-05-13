"""graph_loader.load_graph unit tests against InMemoryClient."""

from __future__ import annotations

import pytest

from mindsos_core.exceptions import PersistenceError
from mindsos_core.persistence import InMemoryClient
from mindsos_core.reconstruction import load_graph


def test_load_graph_raises_when_anchor_missing() -> None:
    c = InMemoryClient()
    c.script([])  # anchor MATCH returns empty
    with pytest.raises(PersistenceError, match="No :Graph row"):
        load_graph(c, "ghost")


def test_load_graph_basic_round_trip_against_scripted_inmemory() -> None:
    """Load a Graph backed by scripted query results from InMemoryClient."""
    c = InMemoryClient()
    # Anchor row.
    c.script([{"name": "g1", "role": "lex", "version": 1, "metagraph_id": None}])
    # Nodes scan.
    c.script([
        {"id": "n1", "type_name": "T", "value": "v1", "version": 1,
         "props": {"k": "x"}}
    ])
    # Edges scan.
    c.script([])
    # Hyperedges scan.
    c.script([])
    # Cross-graph leak detection scan.
    c.script([])
    g = load_graph(c, "graph-id-1")
    assert g.name == "g1"
    assert g.role == "lex"
    assert "n1" in g.nodes
    assert g.nodes["n1"]._version == 1
