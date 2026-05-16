"""P82 — Graph iter_edges / iter_hyperedges / get_edges_for_node with include_deprecated."""

from __future__ import annotations

from mindsos_core import Graph


def _g_with_edges() -> Graph:
    g = Graph(name="t")
    n1 = g.add_node(value="a", type_name="Person")
    n2 = g.add_node(value="b", type_name="Person")
    g.add_edge(source=n1, target=n2, type_name="KNOWS")
    g.add_edge(source=n2, target=n1, type_name="KNOWS")
    g.add_hyperedge(nodes={n1, n2}, type_name="LINKS")
    return g


def test_iter_edges_default_filters_deprecated() -> None:
    g = _g_with_edges()
    e1 = list(g.iter_edges())[0]
    g.deprecate_edge(e1.edge_id)
    edges = list(g.iter_edges())
    assert len(edges) == 1
    assert edges[0].edge_id != e1.edge_id


def test_iter_edges_include_deprecated_passes_all() -> None:
    g = _g_with_edges()
    e1 = list(g.iter_edges())[0]
    g.deprecate_edge(e1.edge_id)
    edges = list(g.iter_edges(include_deprecated=True))
    assert len(edges) == 2


def test_iter_hyperedges_filter() -> None:
    g = _g_with_edges()
    h = list(g.iter_hyperedges())[0]
    g.deprecate_hyperedge(h.edge_id)
    assert len(list(g.iter_hyperedges())) == 0
    assert len(list(g.iter_hyperedges(include_deprecated=True))) == 1


def test_get_edges_for_node_filter() -> None:
    g = _g_with_edges()
    n2 = next(iter(g.nodes.values()))  # any node
    pre = list(g.get_edges_for_node(n2.node_id))
    g.deprecate_edge(pre[0].edge_id)
    post = list(g.get_edges_for_node(n2.node_id))
    assert len(post) < len(pre)
    full = list(g.get_edges_for_node(n2.node_id, include_deprecated=True))
    assert len(full) == len(pre)


def test_disputed_does_not_filter() -> None:
    """ADR-0133 semantic: disputed_at does NOT filter by default."""
    g = _g_with_edges()
    e1 = list(g.iter_edges())[0]
    g.dispute_edge(e1.edge_id)
    edges = list(g.iter_edges())
    assert len(edges) == 2  # still visible
