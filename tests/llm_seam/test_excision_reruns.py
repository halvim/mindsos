"""Excision gate 4 — a model-produced conclusion is RE-RUN without the model.

Plan item I-12 (``docs/plans/MINDSOS_LLM_PLAN.md``), rulings R19, R25, R37,
R41, R42; ADR-0210 amendment 7 clauses 17 and 18.

* every substitute paired with the reader that produced the conclusion is
  dispatched on the source that reader consumed — and no other reader's, and
  no other user's;
* through a dispatcher with NO model bound: one with a client is refused;
* agreement is exact equality of canonical JSON, a refusal's null included;
* a substitute that raises is a failed re-run, never a disagreement;
* no substitute → not yet excisable;
* nothing is written: the graph under examination is unchanged.

The model's answers are RECORDED and replayed. No test here calls a model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture
from tests.phase_30._fixtures import build_session

from mindsos_capacity import Capacity, CapacityLayer
from mindsos_capacity.builtins.comprehension_v0 import register_reader
from mindsos_capacity.builtins.excision_v0 import install_excision_v0
from mindsos_capacity.builtins.origin_v0 import BASIS_STATED
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_COMBINATION,
    CATEGORY_COMPREHENSION,
    datastate_iri,
)
from mindsos_intelligence import L4Dispatcher
from mindsos_intelligence.excision import (
    RERUN_SUBSTITUTE_FAILED,
    RERUN_SUBSTITUTE_WRITES,
    ModelBoundError,
    identify,
    rerun,
)
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline
from mindsos_knowledge import KnowledgeLayer
from mindsos_llm import RecordingStore, RecordedLLM
from mindsos_llm.recording import text_digest, what_was_asked

SOURCE_DS = datastate_iri("excise4.submission_email")
VALUE_DS = datastate_iri("excise4.hospital_stay_asserted")
OTHER_VALUE_DS = datastate_iri("excise4.holiday_asserted")

EMAIL = "I am sorry this is late. I was in hospital for three weeks."
MODEL_ID = "model-x"
MODEL_VERSION = "2026-05-01"
WORDS = "read whether the customer says they were in hospital"
FRAMING = dict(tool_name="extract", tool_description="pull the fields out", max_tokens=1024)
PROMPT_IRI = "prompt:excise4.hospital_stay"
PROMPT_VERSION = 3

READING = {"fields": [{"name": "hospital_stay", "value": True,
                       "quote": "I was in hospital for three weeks", "basis": BASIS_STATED}]}
INVENTED = {"fields": [{"name": "hospital_stay", "value": True,
                        "quote": "words the email does not contain", "basis": BASIS_STATED}]}


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


def _register_source(layer, session=None):
    layer.register_datastate(
        DataState(
            name=SOURCE_DS.split(":", 1)[-1],
            shape=ShapeDescriptor.scalar("str", opaque_tag=SOURCE_DS),
            description="d",
            provenance_category=CATEGORY_COMPREHENSION,
        ),
        session=session,
        allow_new_realm=True,
    )


def _reader(layer, *, name="read_hospital_stay_excise4", value_ds=VALUE_DS, session=None):
    return register_reader(
        layer,
        name=name,
        source_datastate_iri=SOURCE_DS,
        value_datastate_iri=value_ds,
        value_description="Whether a hospital stay is asserted.",
        prompt_iri=PROMPT_IRI,
        prompt_version=PROMPT_VERSION,
        field_name="hospital_stay",
        question="whether the customer says they were in hospital",
        description="Read the customer's assertion of a hospital stay.",
        origin_party_phrase="the customer",
        source_identity_phrase="their submission email",
        expected_basis=BASIS_STATED,
        session=session,
    )


def _layer():
    layer = CapacityLayer()
    install_excision_v0(layer)
    _register_source(layer)
    return layer, _reader(layer)


def _run(reader, answer=READING):
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
        _ReaderDispatcher(reader, llm),
        _Pipeline(steps=(_Step(reader.iri, (SOURCE_DS,)),)),
        initial_inputs={SOURCE_DS: EMAIL},
        request_id="req-excise4",
        mm=mm,
        pipeline_run_ref="pipelinerun:req-excise4:1",
    )
    assert result.success is True
    return mm, result.capacity_graph


def _substitute(reader, body, *, name="rederive_hospital_stay", value_ds=VALUE_DS, writes=False):
    return Capacity(
        name=name,
        category=CATEGORY_COMBINATION,
        inputs=(SOURCE_DS,),
        outputs=(value_ds,),
        implementation=body,
        description="Re-derive the hospital stay without the model.",
        substitute_for=reader.iri,
        writes=writes,
    )


def _says_hospital(**kwargs):
    return {VALUE_DS: "hospital" in kwargs[SOURCE_DS]}


def _dispatcher(layer, *, session=None, llm=None):
    return L4Dispatcher(layer, session=session, kl=KnowledgeLayer.bootstrap(), llm=llm)


def _rerun(layer, graph, **kwargs):
    (conclusion,) = identify([graph])
    return rerun(conclusion, [graph], dispatcher=_dispatcher(layer, **kwargs))


def test_with_no_substitute_the_conclusion_is_not_yet_excisable():
    layer, reader = _layer()
    _, graph = _run(reader)

    report = _rerun(layer, graph)

    assert report.excisable is False
    assert report.reader_iri == reader.iri
    assert report.failure is None
    assert report.runs == ()


def test_a_substitute_that_rederives_the_models_value_agrees():
    layer, reader = _layer()
    sub = _substitute(reader, _says_hospital)
    layer.register_capacity(sub)
    _, graph = _run(reader)

    report = _rerun(layer, graph)

    assert report.excisable is True
    assert report.failure is None
    (run,) = report.runs
    assert (run.substitute_iri, run.agrees, run.value, run.failure) == (sub.iri, True, True, None)


def test_a_substitute_that_rederives_another_value_disagrees():
    layer, reader = _layer()
    layer.register_capacity(_substitute(reader, lambda **kw: {VALUE_DS: False}))
    _, graph = _run(reader)

    (run,) = _rerun(layer, graph).runs

    assert (run.agrees, run.value, run.failure) == (False, False, None)


def test_agreement_is_canonical_json_not_python_equality():
    layer, reader = _layer()
    layer.register_capacity(_substitute(reader, lambda **kw: {VALUE_DS: 1}))
    _, graph = _run(reader)

    (run,) = _rerun(layer, graph).runs

    assert True == 1, "the premise: Python calls these equal"  # noqa: E712
    assert (run.agrees, run.failure) == (False, None)


def test_a_refusals_null_is_a_value_a_substitute_can_agree_with():
    layer, reader = _layer()
    layer.register_capacity(_substitute(reader, lambda **kw: {VALUE_DS: None}))
    _, graph = _run(reader, answer=INVENTED)
    (conclusion,) = identify([graph])
    assert conclusion.record.get("refusal_reason") is not None, "the premise: a refusal"

    (run,) = _rerun(layer, graph).runs

    assert (run.agrees, run.value, run.failure) == (True, None, None)


def test_a_dispatcher_with_a_model_bound_is_refused():
    layer, reader = _layer()
    layer.register_capacity(_substitute(reader, _says_hospital))
    _, graph = _run(reader)

    with pytest.raises(ModelBoundError):
        _rerun(layer, graph, llm=object())


def test_a_substitute_that_raises_is_a_failed_rerun_not_a_disagreement():
    layer, reader = _layer()

    def _raises(**kwargs):
        raise RuntimeError("cannot re-derive")

    layer.register_capacity(_substitute(reader, _raises))
    _, graph = _run(reader)

    (run,) = _rerun(layer, graph).runs

    assert (run.agrees, run.failure) == (None, RERUN_SUBSTITUTE_FAILED)


def test_every_paired_substitute_is_run():
    layer, reader = _layer()
    first = _substitute(reader, _says_hospital, name="a_rederive")
    second = _substitute(reader, lambda **kw: {VALUE_DS: False}, name="b_rederive")
    layer.register_capacity(second)
    layer.register_capacity(first)
    _, graph = _run(reader)

    runs = _rerun(layer, graph).runs

    assert [(r.substitute_iri, r.agrees) for r in runs] == [(first.iri, True), (second.iri, False)]


def test_a_substitute_paired_with_another_reader_is_not_run():
    layer, reader = _layer()
    other = _reader(layer, name="read_holiday_excise4", value_ds=OTHER_VALUE_DS)
    layer.register_capacity(
        _substitute(other, lambda **kw: {OTHER_VALUE_DS: True}, value_ds=OTHER_VALUE_DS)
    )
    _, graph = _run(reader)

    report = _rerun(layer, graph)

    assert report.excisable is False
    assert report.runs == ()


def test_a_substitute_in_another_users_local_is_not_run():
    layer, reader = _layer()
    alice = build_session("alice")
    _register_source(layer, session=alice)
    _reader(layer, session=alice)
    sub = _substitute(reader, _says_hospital)
    layer.register_capacity(sub, session=alice)
    _, graph = _run(reader)

    assert _rerun(layer, graph).excisable is False
    assert _rerun(layer, graph, session=build_session("bob")).excisable is False
    (run,) = _rerun(layer, graph, session=alice).runs
    assert (run.substitute_iri, run.agrees) == (sub.iri, True)


def test_a_substitute_that_declares_writes_is_not_run():
    layer, reader = _layer()
    called = []

    def _body(**kwargs):
        called.append(1)
        return {VALUE_DS: True}

    layer.register_capacity(_substitute(reader, _body, writes=True))
    _, graph = _run(reader)

    (run,) = _rerun(layer, graph).runs

    assert (run.agrees, run.failure) == (None, RERUN_SUBSTITUTE_WRITES)
    assert called == []


def test_a_rerun_leaves_the_graph_under_examination_unchanged():
    layer, reader = _layer()
    layer.register_capacity(_substitute(reader, _says_hospital))
    mm, graph = _run(reader)
    before = (sorted(graph.nodes), sorted(graph.edges), sorted(mm.capacity_mm.graphs))

    _rerun(layer, graph)

    assert (sorted(graph.nodes), sorted(graph.edges), sorted(mm.capacity_mm.graphs)) == before


@pytest.mark.integration
def test_a_stored_reading_is_rerun_after_a_falkordb_round_trip(falkor_client):
    from mindsos_core.reconstruction import load_graph
    from mindsos_intelligence.capacity_persister import persist_capacity_mm
    from mindsos_intelligence.mm_persister import FalkorMMPersister

    layer, reader = _layer()
    layer.register_capacity(_substitute(reader, _says_hospital))
    mm, graph = _run(reader)
    persist_capacity_mm(
        FalkorMMPersister(falkor_client),
        mm.capacity_mm,
        [graph],
        request_id="req-excise4",
        encoders={},
    )
    loaded = load_graph(falkor_client, graph.graph_id)

    (run,) = _rerun(layer, loaded).runs

    assert (run.agrees, run.value, run.failure) == (True, True, None)
