"""Phase 30 — BFS pipeline finder returns the linear 2-step pipeline (ADR-0071)."""

from __future__ import annotations

from mindsos_capacity import PipelineDAG, find_pipeline

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_OUTPUT_IRI,
    build_linear_pipeline_layer,
)


def test_find_pipeline_returns_linear_chain():
    cl = build_linear_pipeline_layer()
    pipeline = find_pipeline(
        cl,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
    )

    assert isinstance(pipeline, PipelineDAG)
    assert pipeline.start_datastates == (DS_INPUT_IRI,)
    assert pipeline.target_datastate == DS_OUTPUT_IRI
    assert len(pipeline) == 2
    iris = [step.capacity_iri for step in pipeline.steps]
    assert iris == [
        "capacity:perception:test.step1",
        "capacity:perception:test.step2",
    ]


def test_pipeline_iter_yields_steps_in_order():
    cl = build_linear_pipeline_layer()
    pipeline = find_pipeline(
        cl,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
    )
    steps_via_iter = list(pipeline)
    assert steps_via_iter == list(pipeline.steps)
