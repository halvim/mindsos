"""A reading — and its refusal — land in the run's grounding graph.

The acceptance-gate-relevant test for the external-model seam. A Decision
Record is rendered from the per-run ``capacity_mm`` grounding graph and
from nothing computed beside it, so everything the Record must say about
a reading has to be *in* that graph: the quote, where it sits in the
document, the model and prompt version that produced it, whether it was
replayed — and, when no value was read, why.

``writer.record`` writes a capacity's **declared outputs**, which is why
a reader declares its reading record as a second output rather than
returning provenance out of band.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from mindsos_capacity.builtins.comprehension_v0 import (
    build_reader,
)
from mindsos_capacity.builtins.origin_v0 import (
    BASIS_STATED,
    ORIGIN_READ_BY_MODEL,
    REFUSAL_QUOTE_NOT_IN_SOURCE,
    origin_record_iri,
)
from mindsos_capacity.identifiers import (
    EDGE_PRODUCES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_DATASTATE_INSTANCE_TYPE,
    datastate_iri,
)
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline
from mindsos_llm import RecordingStore, RecordedLLM, request_key

SOURCE_DS = datastate_iri("claims.submission_email")
VALUE_DS = datastate_iri("claims.hospital_stay_asserted")
RECORD_DS = origin_record_iri(VALUE_DS)

EMAIL = "I am sorry this is late. I was in hospital for three weeks."

MODEL_ID = "model-x"
MODEL_VERSION = "2026-05-01"
PROMPT_IRI = "prompt:claims.hospital_stay"
PROMPT_VERSION = 3


@dataclass
class _Step:
    capacity_iri: str
    input_datastates: Tuple[str, ...]


@dataclass
class _Pipeline:
    steps: Tuple[_Step, ...]


@dataclass
class _Result:
    success: bool
    outputs: Mapping[str, Any] = field(default_factory=dict)
    needs_input: Any = None
    error: Any = None


class _Ctx:
    def __init__(self, llm):
        self.llm = llm


class _ReaderDispatcher:
    """Runs the real reader body with a real llm on the context."""

    def __init__(self, capacity, llm):
        self._capacity = capacity
        self._llm = llm

    def dispatch(self, capacity_iri, inputs, **kwargs):
        outputs = self._capacity.implementation(**dict(inputs), context=_Ctx(self._llm))
        return _Result(success=True, outputs=outputs)


def _reader():
    return build_reader(
        name="read_hospital_stay",
        source_datastate_iri=SOURCE_DS,
        value_datastate_iri=VALUE_DS,
        prompt_iri=PROMPT_IRI,
        prompt_version=PROMPT_VERSION,
        field_name="hospital_stay",
        question="whether the customer says they were in hospital",
        description="Read the customer's assertion of a hospital stay.",
        origin_party_phrase="the customer",
        source_identity_phrase="their submission email",
        expected_basis=BASIS_STATED,
    )


def _llm(fields):
    key = request_key(
        prompt_iri=PROMPT_IRI,
        prompt_version=PROMPT_VERSION,
        model_id=MODEL_ID,
        model_version=MODEL_VERSION,
        temperature=0.0,
        source_text=EMAIL,
    )
    store = RecordingStore({key: {"fields": fields}})
    return RecordedLLM(store, model_id=MODEL_ID, model_version=MODEL_VERSION)


def _run(fields):
    capacity = _reader()
    mm = MentalModel(session_id="s", user_id="u")
    result = execute_pipeline(
        _ReaderDispatcher(capacity, _llm(fields)),
        _Pipeline(steps=(_Step(capacity.iri, (SOURCE_DS,)),)),
        initial_inputs={SOURCE_DS: EMAIL},
        request_id="req-1",
        mm=mm,
        pipeline_run_ref="pipelinerun:req-1:1",
    )
    return capacity, result


def _instances_of(graph, datastate_type):
    return [
        node
        for node in graph.nodes.values()
        if node.type_name == NODE_TYPE_DATASTATE_INSTANCE
        and (node.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE) == datastate_type
    ]


ADMITTED = [
    {
        "name": "hospital_stay",
        "value": True,
        "quote": "I was in hospital for three weeks",
        "basis": BASIS_STATED,
    }
]

FABRICATED = [
    {
        "name": "hospital_stay",
        "value": True,
        "quote": "admitted to St Mary's Hospital on 2 June",
        "basis": BASIS_STATED,
    }
]


def test_the_reading_record_is_a_node_in_the_run_graph():
    capacity, result = _run(ADMITTED)
    assert result.success is True
    graph = result.capacity_graph
    assert graph is not None

    records = _instances_of(graph, RECORD_DS)
    assert len(records) == 1
    record = records[0].value
    # Everything a Decision Record has to be able to state about the
    # reading is in the graph, not beside it.
    assert record["quote"] == "I was in hospital for three weeks"
    assert record["quote_offsets"][0] >= 0
    assert record["model_id"] == MODEL_ID
    assert record["model_version"] == MODEL_VERSION
    assert record["prompt_iri"] == PROMPT_IRI
    assert record["prompt_version"] == PROMPT_VERSION
    assert record["origin_method"] == ORIGIN_READ_BY_MODEL
    assert record["recorded"] is True


def test_the_record_is_wired_to_the_capacity_that_produced_it():
    capacity, result = _run(ADMITTED)
    graph = result.capacity_graph
    cap_nodes = [
        n for n in graph.nodes.values() if n.type_name == NODE_TYPE_CAPACITY_INSTANCE
    ]
    assert len(cap_nodes) == 1
    record_ids = {n.node_id for n in _instances_of(graph, RECORD_DS)}
    produced = {
        e.target.node_id
        for e in graph.edges.values()
        if e.type_name == EDGE_PRODUCES and e.source.node_id == cap_nodes[0].node_id
    }
    assert record_ids <= produced


def test_a_refused_reading_still_puts_its_reason_in_the_graph():
    # The value is absent, so the graph has to carry why — otherwise the
    # Record would state the reason from outside the run.
    capacity, result = _run(FABRICATED)
    assert result.success is True
    graph = result.capacity_graph

    values = _instances_of(graph, VALUE_DS)
    assert len(values) == 1
    assert values[0].value is None

    record = _instances_of(graph, RECORD_DS)[0].value
    assert record["admitted"] is False
    assert record["refusal_reason"] == REFUSAL_QUOTE_NOT_IN_SOURCE
    assert record["claimed_quote"] == "admitted to St Mary's Hospital on 2 June"
