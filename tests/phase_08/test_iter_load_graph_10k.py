"""RPB-12 C — 10K-node opt-in streaming smoke (pytest.mark.slow).

Per Phase 08 row's `Slow tier (@pytest.mark.slow)` entry. Default test
runs exclude this; opt in with ``pytest -m slow``. PB-12 C — assertion
is structural (``len(g.nodes) <= batch_size`` semantics), not memory-
pressure-based.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.slow, pytest.mark.integration]


def test_iter_load_graph_streams_10k_nodes(falkor_client) -> None:
    """Opt-in 10K — verifies the iterator yields + the assembled graph holds all nodes."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import iter_load_graph
    from tests._shared.large_graph_factory import make_large_graph_fixture

    mg = Metagraph(name="10k", identity=IdentityRegistry())
    g = make_large_graph_fixture(
        mg, graph_name="big", n_nodes=10_000, edge_density=0,
    )
    MetagraphRepository(falkor_client).persist(mg)

    yields_seen = 0
    last = None
    for partial in iter_load_graph(
        falkor_client, g.graph_id, batch_size=1_000,
    ):
        yields_seen += 1
        last = partial
    # 10 yields for 10K nodes at batch_size=1K, plus trailer.
    assert yields_seen >= 10
    assert last is not None
    assert len(last.nodes) == 10_000
