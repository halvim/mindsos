"""Phase 30 — find_pipeline obeys max_depth bound."""

from __future__ import annotations

from mindsos_capacity import FIND_BFS_EXHAUSTED, find_pipeline

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_OUTPUT_IRI,
    build_linear_pipeline_layer,
)


def test_max_depth_1_rejects_2_capacity_chain():
    """Linear pipeline is 2 capacities long; max_depth=1 must reject."""
    cl = build_linear_pipeline_layer()

    verdict = find_pipeline(
        cl,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
        max_depth=1,
    )
    assert not verdict.found
    assert verdict.reason == FIND_BFS_EXHAUSTED
    assert "max_depth=1" in verdict.detail


def test_max_depth_2_accepts_2_capacity_chain():
    cl = build_linear_pipeline_layer()
    pipeline = find_pipeline(
        cl,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
        max_depth=2,
    ).pipeline
    assert len(pipeline) == 2
