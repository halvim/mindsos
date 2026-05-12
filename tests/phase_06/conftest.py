"""Shared fixtures for Phase 06 tests."""

from __future__ import annotations

import pytest

from mindsos_core import Graph, Metagraph
import mindsos_instances as mi


@pytest.fixture
def mg() -> Metagraph:
    """Empty metagraph with a registry attached."""
    out = Metagraph(name="MG_TEST")
    mi.attach_registry(out)
    return out


@pytest.fixture
def mg_with_graph(mg) -> Metagraph:
    """Metagraph containing one Graph 'G1' with 3 nodes + 1 edge + 1 hyperedge."""
    g = Graph(name="G1", role="ontology")
    mg.add_graph(g)
    n1 = g.add_node("alice", type_name="Person", properties={"age": 30})
    n2 = g.add_node("bob", type_name="Person", properties={"age": 25})
    n3 = g.add_node("carol", type_name="Person")
    g.add_edge(source=n1, target=n2, type_name="KNOWS", properties={"since": 2020})
    g.add_hyperedge(nodes={n1, n2, n3}, type_name="MEETING")
    return mg


@pytest.fixture
def reg(mg_with_graph) -> "mi.ElementRegistry":
    return mg_with_graph.element_registry  # type: ignore[attr-defined]
