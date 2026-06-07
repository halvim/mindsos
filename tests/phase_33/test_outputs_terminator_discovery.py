"""Phase 33 — write capacities with outputs=() emit zero PRODUCES edges.

Bipartite reframe (ADR-0156, Phase 42): a write capacity is a flow
terminator — it CONSUMES its inputs but PRODUCES no DataState, so it
emits zero ``PRODUCES`` IntergraphEdges. (Pre-Phase-42 this was phrased
as "zero TYPE_COMPAT edges"; TYPE_COMPAT retired with the Phase 29
discovery substrate.) R2 PB-K terminator semantics preserved.
"""

from __future__ import annotations

from mindsos_capacity import (
    CapacityLayer,
    install_consolidate_capacities,
    install_trace_capacities,
)
from mindsos_capacity.identifiers import EDGE_PRODUCES


def _count_produces_edges(metagraph) -> int:
    return sum(
        1
        for ie in metagraph.iter_intergraph_edges()
        if ie.type_name == EDGE_PRODUCES
    )


def test_consolidate_install_emits_zero_produces_edges():
    layer = CapacityLayer()
    install_consolidate_capacities(layer)
    assert _count_produces_edges(layer.global_metagraph()) == 0


def test_trace_install_emits_zero_produces_edges():
    layer = CapacityLayer()
    install_trace_capacities(layer)
    assert _count_produces_edges(layer.global_metagraph()) == 0


def test_both_writer_installs_combined_zero_produces_edges():
    layer = CapacityLayer()
    install_consolidate_capacities(layer)
    install_trace_capacities(layer)
    assert _count_produces_edges(layer.global_metagraph()) == 0
