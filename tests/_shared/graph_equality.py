"""Round-trip graph-equality assertion (Phase 07 — P22 C + P32 A).

``assert_graphs_equal(actual, expected)`` walks the two
:class:`Graph` objects and raises ``AssertionError`` on the first
mismatch (with a contextual message).

Per P32 A — equality belongs in tests, not production. If a caller
passes an :class:`InMemoryClient`-derived "Graph" (call records, not a
real reconstructed Graph), the helper raises a loud :class:`TypeError`
so the misuse is obvious.
"""

from __future__ import annotations


def assert_graphs_equal(actual, expected) -> None:
    """Assert two :class:`Graph` objects are structurally identical.

    Compares node ids/values/types, edges (id + type + endpoints +
    label), hyperedges (id + type + member-set + label). Ignores
    insertion order; uses set comparison via id strings.
    """
    from mindsos_core.models.graph import Graph

    if not isinstance(actual, Graph) or not isinstance(expected, Graph):
        raise TypeError(
            f"assert_graphs_equal requires Graph instances; got "
            f"actual={type(actual).__name__}, expected={type(expected).__name__}. "
            "Did you pass an InMemoryClient or call-record by mistake?"
        )

    assert actual.name == expected.name, (
        f"Graph name mismatch: actual={actual.name!r} expected={expected.name!r}"
    )
    assert actual.role == expected.role, (
        f"Graph role mismatch: actual={actual.role!r} expected={expected.role!r}"
    )

    # Node sets keyed by id.
    a_nodes = {n.node_id: (n.value, n.type_name) for n in actual.nodes.values()}
    e_nodes = {n.node_id: (n.value, n.type_name) for n in expected.nodes.values()}
    assert a_nodes == e_nodes, f"Node sets differ:\n  actual={a_nodes}\n  expected={e_nodes}"

    a_edges = {
        e.edge_id: (e.type_name, e.source.node_id, e.target.node_id, e.label)
        for e in actual.edges.values()
    }
    e_edges = {
        e.edge_id: (e.type_name, e.source.node_id, e.target.node_id, e.label)
        for e in expected.edges.values()
    }
    assert a_edges == e_edges, f"Edge sets differ:\n  actual={a_edges}\n  expected={e_edges}"

    a_he = {
        h.edge_id: (h.type_name, frozenset(n.node_id for n in h.nodes), h.label)
        for h in actual.hyperedges.values()
    }
    e_he = {
        h.edge_id: (h.type_name, frozenset(n.node_id for n in h.nodes), h.label)
        for h in expected.hyperedges.values()
    }
    assert a_he == e_he, f"HyperEdge sets differ:\n  actual={a_he}\n  expected={e_he}"
