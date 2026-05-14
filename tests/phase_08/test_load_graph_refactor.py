"""RR-12 A — load_graph internally calls iter_load_graph + assemble."""

from __future__ import annotations

from mindsos_core.persistence import InMemoryClient
from mindsos_core.reconstruction import iter_load_graph, load_graph


def test_load_graph_result_equivalent_to_iter_assembly() -> None:
    """RR-12 A — load_graph(client, gid) == drain(iter_load_graph(client, gid))."""
    # Build identical InMemoryClient scripts twice.

    def fresh_script() -> InMemoryClient:
        c = InMemoryClient()
        c.script([
            {"name": "g1", "role": "lex", "version": 1, "metagraph_id": None}
        ])
        c.script([
            {"id": "n1", "type_name": "T", "value": "v1", "version": 1, "props": {}},
            {"id": "n2", "type_name": "T", "value": "v2", "version": 1, "props": {}},
        ])
        # Empty trailer.
        c.script([])
        c.script([])
        c.script([])
        return c

    c_load = fresh_script()
    g_load = load_graph(c_load, "g1")

    c_iter = fresh_script()
    last = None
    for partial in iter_load_graph(c_iter, "g1", batch_size=10_000):
        last = partial
    g_iter = last

    assert g_load is not None
    assert g_iter is not None
    assert set(g_load.nodes.keys()) == set(g_iter.nodes.keys())
    assert g_load.name == g_iter.name
    assert g_load.role == g_iter.role


def test_load_graph_preserves_phase_07_surface() -> None:
    """Surface: load_graph(client, graph_id, *, identity=None, schema=None) -> Graph."""
    import inspect

    sig = inspect.signature(load_graph)
    params = list(sig.parameters.keys())
    assert params[0] == "client"
    assert params[1] == "graph_id"
    # kwargs.
    assert "identity" in sig.parameters
    assert "schema" in sig.parameters
