"""Phase 30 — BFS pipeline finder returns empty-steps when start == target."""

from __future__ import annotations

from mindsos_capacity import find_pipeline

from tests.phase_30._fixtures import DS_INPUT_IRI, build_min_layer


def test_find_pipeline_start_equals_target_returns_empty_steps():
    cl = build_min_layer()  # zero capacities; but BFS never runs

    pipeline = find_pipeline(
        cl,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_INPUT_IRI,
    )

    assert pipeline.start_datastates == (DS_INPUT_IRI,)
    assert pipeline.target_datastate == DS_INPUT_IRI
    assert pipeline.steps == ()
    assert len(pipeline) == 0
