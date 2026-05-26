"""Phase 31 — install_text_capacities is idempotent (R1 PB-12 lock).

All-present → no-op return. Tests that calling install twice on a fresh
layer succeeds (second call is no-op) and does not raise.
"""

from __future__ import annotations

from mindsos_capacity.builtins import install_text_capacities

from ._fixtures import make_fresh_layer


def test_install_twice_is_no_op():
    layer = make_fresh_layer()
    install_text_capacities(layer)
    # Second call: no-op (does not raise).
    install_text_capacities(layer)
    # Verify state unchanged — still has the 5 family IRIs.
    global_index = layer._capacity_index[layer.global_metagraph().metagraph_id]
    # 3 DataStates + 2 capacities = 5 family entries (plus any others
    # the layer happened to already have, which on a fresh layer is 0).
    assert len(global_index) == 5
