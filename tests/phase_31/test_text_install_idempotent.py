"""Phase 31 — install_text_capacities is idempotent (R1 PB-12 lock).

All-present → no-op return. Tests that calling install twice on a fresh
layer succeeds (second call is no-op) and does not raise. B-31-T1
hotfix: probe each index correctly (DataStates in ds_graph.nodes;
Capacities in _capacity_index).
"""

from __future__ import annotations

from mindsos_capacity.bootstrap import ensure_datastate_graph
from mindsos_capacity.builtins import install_text_capacities

from ._fixtures import make_fresh_layer


def test_install_twice_is_no_op():
    layer = make_fresh_layer()
    install_text_capacities(layer)
    install_text_capacities(layer)
    ds_graph = ensure_datastate_graph(layer.global_metagraph())
    cap_index = layer._capacity_index[layer.global_metagraph().metagraph_id]
    assert len(ds_graph.nodes) == 3
    assert len(cap_index) == 2
