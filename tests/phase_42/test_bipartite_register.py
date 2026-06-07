"""Phase 42 — register_capacity emits PRODUCES/CONSUMES edges (ADR-0156).

The bipartite reframe: register_capacity walks the declaration's
outputs -> PRODUCES (capacity->DataState) and inputs -> CONSUMES
(DataState->capacity), emitting metagraph-owned IntergraphEdges. The
``inputs``/``outputs`` node-property lists are no longer serialised.
``if_exists="upsert"`` re-emits idempotently.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import Capacity, CapacityLayer, CapacityRegistrationError
from mindsos_capacity.identifiers import (
    CATEGORY_PERCEPTION,
    EDGE_CONSUMES,
    EDGE_PRODUCES,
)

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_MID_IRI,
    DS_OUTPUT_IRI,
    build_linear_pipeline_layer,
    build_min_layer,
    build_step1_capacity,
)


def _edges(mg, type_name):
    return [ie for ie in mg.iter_intergraph_edges() if ie.type_name == type_name]


def test_register_emits_produces_and_consumes_edges():
    cl = build_linear_pipeline_layer()  # step1: input->mid, step2: mid->output
    mg = cl.global_metagraph()
    produces = {(ie.source_node_id, ie.target_node_id) for ie in _edges(mg, EDGE_PRODUCES)}
    consumes = {(ie.source_node_id, ie.target_node_id) for ie in _edges(mg, EDGE_CONSUMES)}
    assert ("capacity:perception:test.step1", DS_MID_IRI) in produces
    assert ("capacity:perception:test.step2", DS_OUTPUT_IRI) in produces
    assert (DS_INPUT_IRI, "capacity:perception:test.step1") in consumes
    assert (DS_MID_IRI, "capacity:perception:test.step2") in consumes
    assert len(produces) == 2 and len(consumes) == 2


def test_inputs_outputs_not_serialised_as_node_properties():
    cl = build_linear_pipeline_layer()
    view = cl.global_view()
    node = view.get_capacity("capacity:perception:test.step1")
    assert "inputs" not in node.properties
    assert "outputs" not in node.properties


def test_default_if_exists_raises_on_duplicate():
    cl = build_min_layer()
    cl.register_capacity(build_step1_capacity())
    with pytest.raises(CapacityRegistrationError):
        cl.register_capacity(build_step1_capacity())


def test_upsert_is_idempotent_no_duplicate_edges():
    cl = build_min_layer()
    cl.register_capacity(build_step1_capacity())
    mg = cl.global_metagraph()
    before_p = len(_edges(mg, EDGE_PRODUCES))
    before_c = len(_edges(mg, EDGE_CONSUMES))
    # Re-register under upsert — must not raise and must not duplicate edges.
    cl.register_capacity(build_step1_capacity(), if_exists="upsert")
    assert len(_edges(mg, EDGE_PRODUCES)) == before_p
    assert len(_edges(mg, EDGE_CONSUMES)) == before_c


def test_contract_field_inline_requires_max_latency_ms():
    cl = build_min_layer()
    bad = Capacity(
        name="test.inline_bad",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        inline=True,  # missing max_latency_ms
    )
    with pytest.raises(CapacityRegistrationError):
        cl.register_capacity(bad)
