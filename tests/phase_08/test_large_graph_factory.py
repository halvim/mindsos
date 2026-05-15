"""RR-13 A — make_large_graph_fixture builds N nodes + density-scaled edges."""

from __future__ import annotations

from mindsos_core.models.identity import IdentityRegistry
from mindsos_core.models.metagraph import Metagraph
from tests._shared.large_graph_factory import make_large_graph_fixture


def test_make_large_graph_fixture_builds_n_nodes() -> None:
    mg = Metagraph(name="m1", identity=IdentityRegistry())
    g = make_large_graph_fixture(
        mg, graph_name="big", role="letters", n_nodes=30, edge_density=1.5,
    )
    assert len(g.nodes) == 30
    # edge_density=1.5 → rounds to 2; n=30; +10 / +20 offset; edges land
    # for indices where i+10 and i+20 < 30. Each node tries to add up to
    # 2 edges (k=1, k=2), but stops early when target index exceeds n.
    # Expected: 20 nodes have k=1 edges (i+10 < 30 means i < 20), 10
    # nodes have k=2 edges (i+20 < 30 means i < 10). Total = 20 + 10 = 30.
    assert len(g.edges) == 30


def test_make_large_graph_fixture_attaches_to_metagraph() -> None:
    mg = Metagraph(name="m1", identity=IdentityRegistry())
    g = make_large_graph_fixture(
        mg, graph_name="small", n_nodes=5, edge_density=0,
    )
    assert g.graph_id in mg.graphs
    assert mg.graphs[g.graph_id] is g
    # edge_density=0 → no edges.
    assert len(g.edges) == 0


def test_make_large_graph_fixture_uses_deterministic_ids() -> None:
    mg = Metagraph(name="m1", identity=IdentityRegistry())
    g = make_large_graph_fixture(
        mg, graph_name="ordered", n_nodes=10, edge_density=0,
    )
    # Ids: node-0 ... node-9 (pad=2).
    expected = {f"node-{i:02d}" for i in range(10)}
    assert set(g.nodes.keys()) == expected
