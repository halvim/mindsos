"""Excision gate 2 — SHOWN: what was asked, verified, and nothing false.

Plan item I-12 (``docs/plans/MINDSOS_LLM_PLAN.md``), rulings R20, R24, R27,
R36, R39, R40; ADR-0210 amendment 7. ``mindsos_intelligence.excision.show``
finds the source text in the grounding graph and the prompt words in the
``prompts`` role, and L3's ``predicate.shown_is_what_ran`` judges them:

* the recomputed ``request_key`` must equal the record's — or the source text,
  schema, framing and model settings are not shown;
* the stored edition's ``text_digest`` must equal the record's
  ``prompt_digest`` — or the words are not shown ("no stored edition matches
  what ran", R36);
* a record keyed under v1 is unverifiable, and a source the walk cannot find
  is named as missing.

The prompt store is a FABRICATED view (the ``prompts`` role's own tests prove
the store); the run graph is real, and the last test reloads it from FalkorDB.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Mapping, Tuple

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.comprehension_v0 import build_reader
from mindsos_capacity.builtins.excision_v0 import (
    SHOWN_KEY_UNVERIFIABLE,
    SHOWN_NO_EDITION_MATCHES,
    SHOWN_NOT_WHAT_RAN,
    SHOWN_SOURCE_NOT_FOUND,
    install_excision_v0,
)
from mindsos_capacity.builtins.origin_v0 import BASIS_STATED
from mindsos_capacity.identifiers import datastate_iri
from mindsos_intelligence import L4Dispatcher
from mindsos_intelligence.excision import identify, show
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.prompts import PROP_PROMPT_IRI, PROP_PROMPT_VERSION
from mindsos_llm import RecordingStore, RecordedLLM
from mindsos_llm.recording import text_digest, what_was_asked

SOURCE_DS = datastate_iri("excise2.submission_email")
VALUE_DS = datastate_iri("excise2.hospital_stay_asserted")

EMAIL = "I am sorry this is late. I was in hospital for three weeks."
MODEL_ID = "model-x"
MODEL_VERSION = "2026-05-01"
WORDS = "read whether the customer says they were in hospital"
SCHEMA = {"type": "object", "properties": {"fields": {"type": "array"}}}
FRAMING = dict(tool_name="extract", tool_description="pull the fields out", max_tokens=1024)
PROMPT_IRI = "prompt:excise2.hospital_stay"
PROMPT_VERSION = 3

READING = {"fields": [{"name": "hospital_stay", "value": True,
                       "quote": "I was in hospital for three weeks", "basis": BASIS_STATED}]}


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


class _PromptView:
    """A fabricated ``prompts`` view: ``iter_nodes`` is the whole protocol."""

    def __init__(self, text=None):
        self._nodes = [] if text is None else [SimpleNamespace(
            properties={PROP_PROMPT_IRI: PROMPT_IRI, PROP_PROMPT_VERSION: str(PROMPT_VERSION)},
            value=text,
        )]

    def iter_nodes(self, role, type_=None):
        return iter(self._nodes)


def _run():
    capacity = build_reader(
        name="read_hospital_stay_excise2",
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
        extraction_schema=SCHEMA,
    )
    key = what_was_asked(
        prompt_iri=PROMPT_IRI,
        prompt_version=PROMPT_VERSION,
        prompt_digest=text_digest(WORDS),
        extraction_schema=SCHEMA,
        model_id=MODEL_ID,
        model_version=MODEL_VERSION,
        temperature=0.0,
        source_text=EMAIL,
        **FRAMING,
    )["request_key"]
    llm = RecordedLLM(
        RecordingStore({key: READING}),
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
        request_id="req-excise2",
        mm=mm,
        pipeline_run_ref="pipelinerun:req-excise2:1",
    )
    assert result.success is True
    return mm, result.capacity_graph


def _dispatcher():
    cl = CapacityLayer()
    install_excision_v0(cl)
    return L4Dispatcher(cl, session=None, kl=KnowledgeLayer.bootstrap())


def _shown(graph, view, conclusion=None, graphs=None):
    if conclusion is None:
        (conclusion,) = identify([graph])
    return show(conclusion, [graph] if graphs is None else graphs, view=view, dispatcher=_dispatcher())


def test_what_ran_is_shown_and_verified():
    _, graph = _run()

    report = _shown(graph, _PromptView(WORDS))

    assert report.verified is True
    assert report.failures == ()
    assert report.prompt_text == WORDS
    assert report.source_text == EMAIL
    assert json.loads(report.extraction_schema) == SCHEMA
    assert report.framing == FRAMING
    assert report.model == {"model_id": MODEL_ID, "model_version": MODEL_VERSION, "temperature": 0.0}


def test_a_stored_edition_that_is_not_what_ran_is_not_shown():
    _, graph = _run()

    report = _shown(graph, _PromptView("read whether the customer was on holiday"))

    assert report.failures == (SHOWN_NO_EDITION_MATCHES,)
    assert report.prompt_text is None
    assert report.source_text == EMAIL


def test_no_stored_edition_is_named_not_filled_in():
    _, graph = _run()

    report = _shown(graph, _PromptView())

    assert report.failures == (SHOWN_NO_EDITION_MATCHES,)
    assert report.prompt_text is None


def test_stamps_that_do_not_reproduce_the_key_show_no_source():
    _, graph = _run()
    (conclusion,) = identify([graph])
    tampered = dataclasses.replace(
        conclusion, record={**conclusion.record, "tool_description": "something else"}
    )

    report = _shown(graph, _PromptView(WORDS), conclusion=tampered)

    assert report.failures == (SHOWN_NOT_WHAT_RAN,)
    assert report.source_text is None
    assert report.extraction_schema is None
    assert report.framing is None
    assert report.prompt_text == WORDS


def test_a_record_keyed_under_v1_is_unverifiable_not_guessed():
    _, graph = _run()
    (conclusion,) = identify([graph])
    record = {k: v for k, v in conclusion.record.items() if k != "key_schema_version"}

    report = _shown(graph, _PromptView(WORDS), conclusion=dataclasses.replace(conclusion, record=record))

    assert report.failures == (SHOWN_KEY_UNVERIFIABLE,)
    assert report.source_text is None


def test_a_source_the_walk_cannot_find_is_named_as_missing():
    _, graph = _run()

    report = _shown(graph, _PromptView(WORDS), graphs=[])

    assert report.failures == (SHOWN_SOURCE_NOT_FOUND,)
    assert report.source_text is None
    assert report.prompt_text == WORDS


@pytest.mark.integration
def test_a_stored_reading_is_shown_and_verified_after_a_falkordb_round_trip(falkor_client):
    from mindsos_core.reconstruction import load_graph
    from mindsos_intelligence.capacity_persister import persist_capacity_mm
    from mindsos_intelligence.mm_persister import FalkorMMPersister

    mm, graph = _run()
    persist_capacity_mm(
        FalkorMMPersister(falkor_client),
        mm.capacity_mm,
        [graph],
        request_id="req-excise2",
        encoders={},
    )
    loaded = load_graph(falkor_client, graph.graph_id)

    report = _shown(loaded, _PromptView(WORDS))

    assert report.verified is True
    assert report.source_text == EMAIL
    assert report.prompt_text == WORDS
