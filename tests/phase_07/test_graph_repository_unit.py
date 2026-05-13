"""GraphRepository unit tests against InMemoryClient (Phase 07)."""

from __future__ import annotations

import pytest

from mindsos_core.exceptions import (
    IntegrityCheckError,
    OptimisticConcurrencyConflict,
)
from mindsos_core.models.graph import Graph
from mindsos_core.persistence import GraphRepository, InMemoryClient


def test_persist_emits_anchor_then_unwind_nodes_edges_hyperedges() -> None:
    g = Graph(name="g")
    n1 = g.add_node("v1", "T")
    n2 = g.add_node("v2", "T")
    g.add_edge(n1, n2, "REL")
    g.add_hyperedge([n1, n2], "HE")

    c = InMemoryClient()
    # Anchor + UNWIND nodes + persist-time check + UNWIND edges + UNWIND hyperedges + persist-time check.
    for _ in range(6):
        c.script([])
    repo = GraphRepository(c)
    repo.persist(g)
    # Expect MERGE :Graph anchor, UNWIND nodes, MATCH Node id check,
    # UNWIND edges, UNWIND hyperedges, MATCH HyperEdge id check.
    queries = [q for q, _ in c.calls]
    assert any("MERGE (g:Graph" in q for q in queries)
    assert any("UNWIND $rows AS row" in q and "Node" in q for q in queries)
    assert any("HyperEdge" in q for q in queries)


def test_persist_time_check_raises_on_duplicate_ids() -> None:
    g = Graph(name="g")
    g.add_node("v", "T", node_id="dup")

    c = InMemoryClient()
    c.script([])  # anchor
    c.script([])  # UNWIND nodes
    c.script([{"id": "dup", "c": 2}])  # duplicate scan returns dup
    repo = GraphRepository(c)
    with pytest.raises(IntegrityCheckError, match="dup"):
        repo.persist(g)


def test_update_node_properties_returns_new_version() -> None:
    c = InMemoryClient()
    c.script([{"id": "n1", "version": 7}])
    repo = GraphRepository(c)
    v = repo.update_node_properties("g1", "n1", {"k": "v"})
    assert v == 7


def test_update_node_properties_occ_predicate_when_expected_given() -> None:
    c = InMemoryClient()
    c.script([])  # stale → zero rows
    repo = GraphRepository(c)
    with pytest.raises(OptimisticConcurrencyConflict) as exc:
        repo.update_node_properties("g1", "n1", {"k": "v"}, expected_version=3)
    assert exc.value.expected_version == 3


def test_update_missing_target_without_expected_raises_integrity_check() -> None:
    c = InMemoryClient()
    c.script([])  # No row, no expected_version → IntegrityCheckError
    repo = GraphRepository(c)
    with pytest.raises(IntegrityCheckError, match="not present"):
        repo.update_node_properties("g1", "missing", {"k": "v"})


def test_update_edge_and_hyperedge_paths() -> None:
    c = InMemoryClient()
    c.script([{"id": "e1", "version": 2}])
    c.script([{"id": "h1", "version": 3}])
    repo = GraphRepository(c)
    assert repo.update_edge_properties("g1", "e1", {"k": "v"}) == 2
    assert repo.update_hyperedge_properties("g1", "h1", {"k": "v"}) == 3


def test_remove_emits_tombstone_then_detach_delete() -> None:
    c = InMemoryClient()
    repo = GraphRepository(c)
    repo.remove_node("g1", "n1")
    repo.remove_edge("g1", "e1")
    repo.remove_hyperedge("g1", "h1")
    queries = [q for q, _ in c.calls]
    assert all(":Tombstone {graph_id: $gid, element_id" in q for q in queries)
    assert any("DETACH DELETE n" in q for q in queries)
    assert any("DELETE e" in q for q in queries)
    assert any("DETACH DELETE h" in q for q in queries)
