"""Excision gate 1 — IDENTIFY: every conclusion the borrowed model produced.

Plan item I-12 (``docs/plans/MINDSOS_LLM_PLAN.md``), rulings R26, R27, R38;
ADR-0210 amendment 7. ``mindsos_intelligence.excision.identify`` lists, from a
run's grounding graphs, every origin record whose ``origin_method`` is
``read_by_model`` — a reading and a refusal the model produced alike — and
nothing else: not a record another producer wrote, not an
``environment_fault`` refusal (no reading happened).

The two negative cases are FABRICATED records (the lane's birth-certificate
move): no producer in the tree writes an ``environment_fault`` record today,
so a guard that waited for one could never go red.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Mapping, Tuple

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture

from mindsos_capacity.builtins.comprehension_v0 import build_reader
from mindsos_capacity.builtins.origin_v0 import (
    BASIS_STATED,
    ORIGIN_READ_BY_MODEL,
    ORIGIN_READ_FROM_SOURCE,
    REFUSAL_FIELD_ABSENT,
    REFUSAL_MODEL_UNREACHABLE,
    origin_record_iri,
)
from mindsos_capacity.identifiers import (
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_DATASTATE_INSTANCE_TYPE,
    datastate_iri,
)
from mindsos_intelligence.excision import identify
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline
from mindsos_llm import RecordingStore, RecordedLLM
from mindsos_llm.recording import text_digest, what_was_asked

SOURCE_DS = datastate_iri("excise1.submission_email")
VALUE_DS = datastate_iri("excise1.hospital_stay_asserted")
RECORD_DS = origin_record_iri(VALUE_DS)

EMAIL = "I am sorry this is late. I was in hospital for three weeks."
MODEL_ID = "model-x"
MODEL_VERSION = "2026-05-01"
WORDS = "read whether the customer says they were in hospital"
FRAMING = dict(tool_name="extract", tool_description="pull the fields out", max_tokens=1024)
PROMPT_IRI = "prompt:excise1.hospital_stay"
PROMPT_VERSION = 1

READING = {"fields": [{"name": "hospital_stay", "value": True,
                       "quote": "I was in hospital for three weeks", "basis": BASIS_STATED}]}
NO_SUCH_FIELD = {"fields": [{"name": "something_else", "value": 1, "quote": "sorry"}]}


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
    def __init__(self, capacity, llm):
        self._capacity = capacity
        self._llm = llm

    def dispatch(self, capacity_iri, inputs, **kwargs):
        outputs = self._capacity.implementation(**dict(inputs), context=_Ctx(self._llm))
        return _Result(success=True, outputs=outputs)


def _run(answer):
    capacity = build_reader(
        name="read_hospital_stay_excise1",
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
        RecordingStore({key: answer}),
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
        request_id="req-excise1",
        mm=mm,
        pipeline_run_ref="pipelinerun:req-excise1:1",
    )
    assert result.success is True
    return mm, result.capacity_graph


def _fabricated_graph(record):
    node = SimpleNamespace(
        node_id="n1",
        type_name=NODE_TYPE_DATASTATE_INSTANCE,
        properties={PROP_DATASTATE_INSTANCE_TYPE: RECORD_DS},
        value=record,
    )
    return SimpleNamespace(graph_id="g-fabricated", nodes={"n1": node})


def test_a_reading_is_identified_as_the_model_s():
    _, graph = _run(READING)

    found = identify([graph])

    assert [c.value_datastate for c in found] == [VALUE_DS]
    assert found[0].record["origin_method"] == ORIGIN_READ_BY_MODEL
    assert found[0].record["refusal_reason"] is None


def test_a_refusal_the_model_produced_is_identified():
    _, graph = _run(NO_SUCH_FIELD)

    found = identify([graph])

    assert [c.value_datastate for c in found] == [VALUE_DS]
    assert found[0].record["refusal_reason"] == REFUSAL_FIELD_ABSENT


def test_a_record_another_producer_wrote_is_not_identified():
    record = {"origin_method": ORIGIN_READ_FROM_SOURCE, "environment_fault": False}

    assert identify([_fabricated_graph(record)]) == ()


def test_an_environment_fault_refusal_is_not_identified():
    record = {
        "origin_method": ORIGIN_READ_BY_MODEL,
        "refusal_reason": REFUSAL_MODEL_UNREACHABLE,
        "environment_fault": True,
    }

    assert identify([_fabricated_graph(record)]) == ()


@pytest.mark.integration
def test_a_stored_reading_is_identified_after_a_falkordb_round_trip(falkor_client):
    from mindsos_core.reconstruction import load_graph
    from mindsos_intelligence.capacity_persister import persist_capacity_mm
    from mindsos_intelligence.mm_persister import FalkorMMPersister

    mm, graph = _run(READING)
    persist_capacity_mm(
        FalkorMMPersister(falkor_client),
        mm.capacity_mm,
        [graph],
        request_id="req-excise1",
        encoders={},
    )
    loaded = load_graph(falkor_client, graph.graph_id)

    def _named(found):
        return [(c.value_datastate, c.record["request_key"]) for c in found]

    assert len(identify([loaded])) == 1
    assert _named(identify([loaded])) == _named(identify([graph]))
