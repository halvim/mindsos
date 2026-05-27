"""Phase 33 — write capacities with outputs=() emit zero TYPE_COMPAT edges.

R2 PB-K confirmation: write-capacity terminator semantics — they
consume but emit nothing into the DataState flow graph.
"""

from __future__ import annotations

from mindsos_capacity import (
    CapacityLayer,
    install_consolidate_capacities,
    install_trace_capacities,
)
from mindsos_capacity.identifiers import EDGE_TYPE_COMPAT


def _count_type_compat_edges(metagraph) -> int:
    n = 0
    for g in metagraph.graphs.values():
        for e in g.edges.values():
            if e.type_name == EDGE_TYPE_COMPAT:
                n += 1
    return n


def test_consolidate_install_emits_zero_typecompat_edges():
    layer = CapacityLayer()
    install_consolidate_capacities(layer)
    assert _count_type_compat_edges(layer.global_metagraph()) == 0


def test_trace_install_emits_zero_typecompat_edges():
    layer = CapacityLayer()
    install_trace_capacities(layer)
    assert _count_type_compat_edges(layer.global_metagraph()) == 0


def test_both_writer_installs_combined_zero_typecompat_edges():
    layer = CapacityLayer()
    install_consolidate_capacities(layer)
    install_trace_capacities(layer)
    assert _count_type_compat_edges(layer.global_metagraph()) == 0
