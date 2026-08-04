"""Phase 30 — find_pipeline returns a not-found verdict on exhaustion.

CORE-C3R1 (shim **S4**): "no path exists" is a verdict about the world, not a
technical failure, so it is **returned** rather than raised (ADR-0206 §3). This
file previously asserted ``PipelineNotFoundError`` under ADR-0072's "L3 raises
for its own invariants" carve-out; that carve-out no longer applies here,
because no-route was never an implementation error.
"""

from __future__ import annotations

from mindsos_capacity import FIND_BFS_EXHAUSTED, FIND_REASONS, find_pipeline

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_OUTPUT_IRI,
    build_min_layer,
)


def test_find_pipeline_empty_layer_returns_not_found():
    cl = build_min_layer()  # zero capacities

    verdict = find_pipeline(
        cl,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
    )

    assert not verdict.found
    assert verdict.pipeline is None
    assert verdict.reason == FIND_BFS_EXHAUSTED
    assert verdict.reason in FIND_REASONS
    assert "datastate:test.input" in verdict.detail
    assert "datastate:test.output" in verdict.detail
    assert "max_depth" in verdict.detail
    assert verdict.unproducible == {}
