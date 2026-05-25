"""Phase 30 — find_pipeline raises PipelineNotFoundError on exhaustion.

ADR-0072 §Decision carve-out: L3 raises for its own invariants. "No
path exists" is an L3 invariant of the query, not an implementation
error in a bound capacity callable.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import PipelineNotFoundError, find_pipeline

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_OUTPUT_IRI,
    build_min_layer,
)


def test_find_pipeline_empty_layer_raises():
    cl = build_min_layer()  # zero capacities

    with pytest.raises(PipelineNotFoundError) as exc_info:
        find_pipeline(
            cl,
            start_datastate=DS_INPUT_IRI,
            target_datastate=DS_OUTPUT_IRI,
        )

    msg = str(exc_info.value)
    assert "datastate:test.input" in msg
    assert "datastate:test.output" in msg
    assert "max_depth" in msg
