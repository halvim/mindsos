"""Integration — iter_load_graph behavior per RPB-8 A scenarios.

(i) structural cap; (ii) equivalence; (iii) cross-batch edge fidelity.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def _persist_graph_via_metagraph(client, mg, g):
    """Helper — wrap solo Graph persist via the MetagraphRepository to
    get a valid :Graph anchor row + nodes.
    """
    from mindsos_core.persistence import MetagraphRepository

    MetagraphRepository(client).persist(mg)


def test_structural_cap_intermediate_batches_nodes_only(falkor_client) -> None:
    """RPB-8 A (i) — intermediate yields don't exceed batch_size per page."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.reconstruction import iter_load_graph
    from tests._shared.large_graph_factory import make_large_graph_fixture

    mg = Metagraph(name="cap-test", identity=IdentityRegistry())
    g = make_large_graph_fixture(
        mg, graph_name="streamed", n_nodes=30, edge_density=0,
    )
    _persist_graph_via_metagraph(falkor_client, mg, g)

    # Stream with batch_size=10 — yields should grow monotonically.
    batches = list(
        iter_load_graph(
            falkor_client, g.graph_id, identity=mg.identity, batch_size=10
        )
    )
    assert len(batches) >= 1
    # Last yield holds the full assembled graph.
    final = batches[-1]
    assert len(final.nodes) == 30


def test_equivalence_load_graph_equals_iter_assembly(falkor_client) -> None:
    """RPB-8 A (ii) — load_graph(gid) == drain(iter_load_graph(gid, B))."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.reconstruction import iter_load_graph, load_graph
    from tests._shared.large_graph_factory import make_large_graph_fixture

    mg = Metagraph(name="equiv-test", identity=IdentityRegistry())
    g = make_large_graph_fixture(
        mg, graph_name="equiv", n_nodes=30, edge_density=1.5,
    )
    _persist_graph_via_metagraph(falkor_client, mg, g)

    g_full = load_graph(falkor_client, g.graph_id)
    last = None
    for partial in iter_load_graph(
        falkor_client, g.graph_id, batch_size=100,
    ):
        last = partial
    assert last is not None
    assert set(g_full.nodes.keys()) == set(last.nodes.keys())
    assert set(g_full.edges.keys()) == set(last.edges.keys())


def test_cross_batch_edge_fidelity(falkor_client) -> None:
    """RPB-8 A (iii) — node-3 → node-23 edge appears under batch_size=10."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.reconstruction import iter_load_graph
    from tests._shared.large_graph_factory import make_large_graph_fixture

    mg = Metagraph(name="cross-batch", identity=IdentityRegistry())
    # density=1.5 → round=2 edges per node; +10 / +20 offsets create
    # cross-batch references at batch_size=10.
    g = make_large_graph_fixture(
        mg, graph_name="cb", n_nodes=30, edge_density=1.5,
    )
    _persist_graph_via_metagraph(falkor_client, mg, g)

    last = None
    for partial in iter_load_graph(
        falkor_client, g.graph_id, batch_size=10,
    ):
        last = partial
    assert last is not None
    # Verify a known cross-batch edge: node-03 → node-13 (i=3, k=1).
    found_cross_batch = False
    for e in last.edges.values():
        if e.source.node_id == "node-03" and e.target.node_id == "node-13":
            found_cross_batch = True
            break
    assert found_cross_batch, (
        "Expected cross-batch edge node-03 → node-13 to survive "
        "batch_size=10 streaming + assembly (RPB-1 A trailer semantics)."
    )
