"""Phase 30 — find_pipeline obeys max_depth bound."""

from __future__ import annotations

import pytest

from mindsos_capacity import PipelineNotFoundError, find_pipeline

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_OUTPUT_IRI,
    build_linear_pipeline_layer,
)


def test_max_depth_1_rejects_2_capacity_chain():
    """Linear pipeline is 2 capacities long; max_depth=1 must reject."""
    cl = build_linear_pipeline_layer()

    with pytest.raises(PipelineNotFoundError) as exc_info:
        find_pipeline(
            cl,
            start_datastate=DS_INPUT_IRI,
            target_datastate=DS_OUTPUT_IRI,
            max_depth=1,
        )
    assert "max_depth=1" in str(exc_info.value)


def test_max_depth_2_accepts_2_capacity_chain():
    cl = build_linear_pipeline_layer()
    pipeline = find_pipeline(
        cl,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
        max_depth=2,
    )
    assert len(pipeline) == 2
