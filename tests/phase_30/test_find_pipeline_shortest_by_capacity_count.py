"""Phase 30 — BFS returns shortest by CAPACITY count (R2 PB-34 sentinel; ADR-0071).

Branching-capacity fixture: a single ``test.multi`` capacity has TWO
outputs — ``test.fork`` and ``test.x``. From fork, a 1-capacity path
reaches output (total 2 capacities). From x, a 3-capacity chain
(x→y→z→output) reaches output (total 4 capacities). BFS must pick the
2-capacity path. The invariant locked by this test: BFS counts
capacity invocations, not graph edges.
"""

from __future__ import annotations

from mindsos_capacity import find_pipeline

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_OUTPUT_IRI,
    build_branching_capacity_layer,
)


def test_bfs_picks_shortest_capacity_count_path():
    cl = build_branching_capacity_layer()
    pipeline = find_pipeline(
        cl,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
        max_depth=8,
    ).pipeline
    # 2-capacity path: test.multi → fork → test.fork_to_output → output
    assert len(pipeline) == 2
    iris = [step.capacity_iri for step in pipeline.steps]
    assert iris == [
        "capacity:perception:test.multi",
        "capacity:perception:test.fork_to_output",
    ]
