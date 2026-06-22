"""Phase 42 — find_pipeline + view walks over the bipartite edge set.

Semantic-preservation: the Phase 30 BFS cases must yield identical
pipelines now that the walk reads PRODUCES/CONSUMES IntergraphEdges
(ADR-0156) rather than node ``inputs``/``outputs`` properties or the
retired TYPE_COMPAT edges. Also exercises the rewritten view helpers
``successors_of`` / ``inputs_of`` / ``outputs_of`` / ``producers_of`` /
``consumers_of``.
"""

from __future__ import annotations

from mindsos_capacity import PipelineDAG, find_pipeline

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_MID_IRI,
    DS_OUTPUT_IRI,
    build_branching_capacity_layer,
    build_linear_pipeline_layer,
)

STEP1 = "capacity:perception:test.step1"
STEP2 = "capacity:perception:test.step2"


def test_linear_pipeline_semantics_preserved():
    cl = build_linear_pipeline_layer()
    pipeline = find_pipeline(
        cl, start_datastate=DS_INPUT_IRI, target_datastate=DS_OUTPUT_IRI
    )
    assert isinstance(pipeline, PipelineDAG)
    assert [s.capacity_iri for s in pipeline.steps] == [STEP1, STEP2]


def test_shortest_by_capacity_count_preserved():
    cl = build_branching_capacity_layer()
    pipeline = find_pipeline(
        cl, start_datastate=DS_INPUT_IRI, target_datastate=DS_OUTPUT_IRI
    )
    # The 2-capacity path (multi -> fork_to_output) beats the 4-capacity path.
    assert len(pipeline) == 2


def test_outputs_of_and_inputs_of_edge_sourced():
    cl = build_linear_pipeline_layer()
    view = cl.global_view()
    assert view.outputs_of(STEP1) == [DS_MID_IRI]
    assert view.inputs_of(STEP1) == [DS_INPUT_IRI]
    assert view.outputs_of(STEP2) == [DS_OUTPUT_IRI]
    assert view.inputs_of(STEP2) == [DS_MID_IRI]


def test_successors_of_two_hop_walk():
    cl = build_linear_pipeline_layer()
    view = cl.global_view()
    # step1 -> PRODUCES test.mid -> CONSUMES -> step2
    assert view.successors_of(STEP1) == [STEP2]
    # step2 produces test.output, which nothing consumes -> no successor
    assert view.successors_of(STEP2) == []


def test_producers_and_consumers_of_datastate():
    cl = build_linear_pipeline_layer()
    view = cl.global_view()
    producers = [n.node_id for n in view.producers_of(DS_MID_IRI)]
    consumers = [n.node_id for n in view.consumers_of(DS_MID_IRI)]
    assert producers == [STEP1]
    assert consumers == [STEP2]
