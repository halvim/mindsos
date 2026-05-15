"""RR-2 D — load_metagraph(..., batch_size=N) routes through iter_load_graph."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_load_metagraph_with_batch_size_equivalent_to_full(falkor_client) -> None:
    """Round-trip equivalence: batch_size=100 ≡ batch_size=None per RR-2 D."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import load_metagraph
    from tests._shared.large_graph_factory import make_large_graph_fixture
    from tests._shared.metagraph_equality import assert_metagraphs_equal

    mg = Metagraph(name="m1", identity=IdentityRegistry())
    g = make_large_graph_fixture(
        mg, graph_name="streamed", n_nodes=50, edge_density=1.0,
    )
    MetagraphRepository(falkor_client).persist(mg)

    mg_full = load_metagraph(falkor_client, mg.metagraph_id, batch_size=None)
    mg_batched = load_metagraph(falkor_client, mg.metagraph_id, batch_size=10)

    # Both round-trips produce structurally identical metagraphs.
    assert_metagraphs_equal(mg_full, mg_batched)
