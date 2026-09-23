"""A stored reading reaches the document it was read from — plan R27.

``mindsos_llm`` plan item I-12 re-runs a model-produced conclusion without the
model (R19) and shows what was asked (R20, R24). Both need the SOURCE TEXT, and
the origin record does not hold it: it names the source DataState's *type*, a
quote and its offsets, and a ``request_key`` that hashes the text one way. The
recorded set does not hold it either — a payload carries the answer only.

The one place the text lives is the run's grounding graph: the source instance
is seeded by ``execute_pipeline``, and ``CapacityMMWriter.record`` wires it
``CONSUMES`` into the reader's CapacityInstance, which ``PRODUCES`` the origin
record. This file proves that path — live, and after a persist + reload from
FalkorDB, which is the only sense in which a conclusion is STORED (R27's
domain: conclusions in a persisted Episode's grounding graph).

⚠ The walk is checked against the record's own ``request_key``: the text found
is the text that was read only if recomputing the key from the record's stamped
fields and that text reproduces it. A walk that found *some* string of the
right DataState would otherwise pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture

from mindsos_capacity.builtins.comprehension_v0 import build_reader
from mindsos_capacity.builtins.origin_v0 import (
    BASIS_STATED,
    ORIGIN_READ_BY_MODEL,
    origin_record_iri,
)
from mindsos_capacity.identifiers import (
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_DATASTATE_INSTANCE_TYPE,
    datastate_iri,
)
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline
from mindsos_llm import RecordingStore, RecordedLLM
from mindsos_llm.recording import text_digest, what_was_asked

SOURCE_DS = datastate_iri("excision.submission_email")
VALUE_DS = datastate_iri("excision.hospital_stay_asserted")
RECORD_DS = origin_record_iri(VALUE_DS)

EMAIL = "I am sorry this is late. I was in hospital for three weeks."
OTHER_EMAIL = "I am sorry this is late. I was on holiday for three weeks."

MODEL_ID = "model-x"
MODEL_VERSION = "2026-05-01"
#: What the model is asked besides the document (plan R21, R22): the replay
#: client hashes the digest of these words and this framing into the v2 key.
WORDS = "read whether the customer says they were in hospital"
FRAMING = dict(tool_name="extract", tool_description="pull the fields out", max_tokens=1024)
PROMPT_IRI = "prompt:excision.hospital_stay"
PROMPT_VERSION = 3

ANSWER = [
    {
        "name": "hospital_stay",
        "value": True,
        "quote": "I was in hospital for three weeks",
        "basis": BASIS_STATED,
    }
]


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
    """Runs the real reader body with a real replay client on the context."""

    def __init__(self, capacity, llm):
        self._capacity = capacity
        self._llm = llm

    def dispatch(self, capacity_iri, inputs, **kwargs):
        outputs = self._capacity.implementation(**dict(inputs), context=_Ctx(self._llm))
        return _Result(success=True, outputs=outputs)


def _run():
    capacity = build_reader(
        name="read_hospital_stay_excision",
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
    key = what_was_asked(
        prompt_iri=PROMPT_IRI,
        prompt_version=PROMPT_VERSION,
        prompt_digest=text_digest(WORDS),
        extraction_schema=None,
        model_id=MODEL_ID,
        model_version=MODEL_VERSION,
        temperature=0.0,
        source_text=EMAIL,
        **FRAMING,
    )["request_key"]
    llm = RecordedLLM(
        RecordingStore({key: {"fields": ANSWER}}),
        model_id=MODEL_ID,
        model_version=MODEL_VERSION,
        resolve_prompt=lambda **_: WORDS,
        **FRAMING,
    )
    mm = MentalModel(session_id="s", user_id="u")
    result = execute_pipeline(
        _ReaderDispatcher(capacity, llm),
        _Pipeline(steps=(_Step(capacity.iri, (SOURCE_DS,)),)),
        initial_inputs={SOURCE_DS: EMAIL},
        request_id="req-excision",
        mm=mm,
        pipeline_run_ref="pipelinerun:req-excision:1",
    )
    assert result.success is True
    return mm, result.capacity_graph


def _only(nodes, what):
    nodes = list(nodes)
    assert len(nodes) == 1, f"expected one {what}, found {len(nodes)}"
    return nodes[0]


def _instance_type(node):
    return (node.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)


def _source_text_of(graph, record_node):
    """record <-PRODUCES- CapacityInstance <-CONSUMES- source instance."""
    producer = _only(
        (
            e.source
            for e in graph.edges.values()
            if e.type_name == EDGE_PRODUCES
            and e.target.node_id == record_node.node_id
            and e.source.type_name == NODE_TYPE_CAPACITY_INSTANCE
        ),
        "producing CapacityInstance",
    )
    source = _only(
        (
            e.source
            for e in graph.edges.values()
            if e.type_name == EDGE_CONSUMES
            and e.target.node_id == producer.node_id
            and _instance_type(e.source) == SOURCE_DS
        ),
        "consumed source instance",
    )
    return source.value


def _key_from(record, source_text):
    """Recompute the v2 key from the record plus the source text found.

    ⚠ I-17 gate 2 (plan R22): the prompt digest, the schema and the framing
    are hashed into the key, and the origin record does not carry them until
    gate 3 (R23, R32). Until then they are this file's own constants — which
    still proves what this file claims: only the source text actually read
    reproduces the record's key. Gate 3 reads them off the record instead.
    """
    return what_was_asked(
        prompt_iri=record["prompt_iri"],
        prompt_version=record["prompt_version"],
        prompt_digest=text_digest(WORDS),
        extraction_schema=None,
        model_id=record["model_id"],
        model_version=record["model_version"],
        temperature=record["temperature"],
        source_text=source_text,
        **FRAMING,
    )["request_key"]


def _record_node(graph):
    return _only(
        (
            n
            for n in graph.nodes.values()
            if n.type_name == NODE_TYPE_DATASTATE_INSTANCE
            and _instance_type(n) == RECORD_DS
        ),
        "origin record",
    )


def test_a_live_reading_reaches_the_text_it_was_read_from():
    _, graph = _run()
    record_node = _record_node(graph)
    record = record_node.value
    assert record["origin_method"] == ORIGIN_READ_BY_MODEL

    text = _source_text_of(graph, record_node)

    assert text == EMAIL
    assert _key_from(record, text) == record["request_key"]


def test_the_key_check_refuses_a_text_that_was_not_read():
    """The other door: a different document does not reproduce the key, so the
    check above cannot pass on any string of the right DataState."""
    _, graph = _run()
    record = _record_node(graph).value

    assert _key_from(record, OTHER_EMAIL) != record["request_key"]


@pytest.mark.integration
def test_a_stored_reading_reaches_the_text_it_was_read_from(falkor_client):
    from mindsos_core.reconstruction import load_graph
    from mindsos_intelligence.capacity_persister import persist_capacity_mm
    from mindsos_intelligence.mm_persister import FalkorMMPersister

    mm, graph = _run()
    persist_capacity_mm(
        FalkorMMPersister(falkor_client),
        mm.capacity_mm,
        [graph],
        request_id="req-excision",
        encoders={},
    )
    loaded = load_graph(falkor_client, graph.graph_id)
    record_node = _record_node(loaded)
    record = record_node.value

    text = _source_text_of(loaded, record_node)

    assert text == EMAIL
    assert _key_from(record, text) == record["request_key"]
