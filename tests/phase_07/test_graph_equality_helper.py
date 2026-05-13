"""tests/_shared/graph_equality.py contract tests (P22 C + P32 A)."""

from __future__ import annotations

import pytest

from mindsos_core.models.graph import Graph
from tests._shared.graph_equality import assert_graphs_equal


def test_equal_graphs_pass() -> None:
    g1 = Graph(name="g")
    g2 = Graph(name="g")
    assert_graphs_equal(g1, g2)


def test_name_mismatch_raises() -> None:
    g1 = Graph(name="a")
    g2 = Graph(name="b")
    with pytest.raises(AssertionError, match="Graph name mismatch"):
        assert_graphs_equal(g1, g2)


def test_node_diff_raises() -> None:
    g1 = Graph(name="g")
    g2 = Graph(name="g")
    g1.add_node("v1", "T", node_id="n1")
    g2.add_node("v2", "T", node_id="n1")
    with pytest.raises(AssertionError, match="Node sets differ"):
        assert_graphs_equal(g1, g2)


def test_non_graph_inputs_raise_typeerror() -> None:
    """P32 A — InMemoryClient or call records → loud TypeError."""
    from mindsos_core.persistence import InMemoryClient

    g = Graph(name="g")
    c = InMemoryClient()
    with pytest.raises(TypeError, match="requires Graph instances"):
        assert_graphs_equal(c, g)
