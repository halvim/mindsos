"""Re-run withholds the model's answer, and re-checks the pairing (I-18 gate 2).

``docs/plans/MINDSOS_LLM_PLAN.md`` rulings R44(d) and R45; ADR-0210 amendment 8
clauses 4 and 5. A conclusion minted by an ANSWER-FED reader — one handed the
model's answer — is re-run by a substitute that is given the source only.

The pairing is checked at registration, and it can stop holding afterwards:
``register_capacity(if_exists="upsert")`` re-binds a reader's declaration, and
a Local reader shadows the Global one of the same IRI. So *re-run* checks the
pairing again, against the reader as declared where the re-run happens; a
substitute that no longer pairs is named and NOT run.

No test here calls a model: the "answer" is a value handed to the run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from tests.phase_30._fixtures import build_session

from mindsos_capacity import Capacity, CapacityLayer
from mindsos_capacity.builtins.comprehension_v0 import reader_datastates
from mindsos_capacity.builtins.excision_v0 import install_excision_v0
from mindsos_capacity.builtins.origin_v0 import (
    ORIGIN_READ_BY_MODEL,
    PRODUCER_DOCUMENT_READING,
    build_origin_record,
    origin_record_iri,
)
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_COMBINATION,
    CATEGORY_COMPREHENSION,
    datastate_iri,
)
from mindsos_intelligence import L4Dispatcher
from mindsos_intelligence.excision import identify, rerun
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline
from mindsos_knowledge import KnowledgeLayer

ANSWER_DS = datastate_iri("answerfed2.model_answer")
EXTRA_DS = datastate_iri("answerfed2.matter")
SOURCE_DS = datastate_iri("answerfed2.message")
VALUE_DS = datastate_iri("answerfed2.amount_claimed")
RECORD_DS = origin_record_iri(VALUE_DS)

ANSWER = {"amount": 120}
MESSAGE = "I am claiming 120 for the repair."
MATTER = "the repair"

#: The failure *re-run* names when a substitute no longer pairs (plan R45).
NO_LONGER_PAIRS = "substitute_no_longer_pairs"


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


class _DirectDispatcher:
    def __init__(self, capacity):
        self._capacity = capacity

    def dispatch(self, capacity_iri, inputs, **kwargs):
        return _Result(success=True, outputs=self._capacity.implementation(**dict(inputs)))


def _mint(**kwargs):
    return {
        VALUE_DS: kwargs[ANSWER_DS]["amount"],
        RECORD_DS: build_origin_record(
            producer_kind=PRODUCER_DOCUMENT_READING,
            origin_method=ORIGIN_READ_BY_MODEL,
            source_identity_phrase="their message",
            source_datastate=SOURCE_DS,
            question="the amount claimed",
            admitted=True,
            supplied_fields=(),
            possible_refusal_reasons=(),
        ),
    }


def _layer():
    layer = CapacityLayer()
    install_excision_v0(layer)
    for iri, kind in ((ANSWER_DS, "opaque"), (EXTRA_DS, "str"), (SOURCE_DS, "str")):
        name = iri.split(":", 1)[-1]
        shape = (
            ShapeDescriptor.opaque(name)
            if kind == "opaque"
            else ShapeDescriptor.scalar(kind, opaque_tag=iri)
        )
        layer.register_datastate(
            DataState(name=name, shape=shape, description="d",
                      provenance_category=CATEGORY_COMPREHENSION),
            allow_new_realm=True,
        )
    for datastate in reader_datastates(
        value_datastate_iri=VALUE_DS, value_description="The amount claimed."
    ):
        layer.register_datastate(datastate, allow_new_realm=True)
    return layer


def _reader(inputs, answer_inputs):
    return Capacity(
        name="mint_amount_claimed2",
        category=CATEGORY_COMPREHENSION,
        inputs=inputs,
        outputs=(VALUE_DS, RECORD_DS),
        implementation=_mint,
        description="Mint the amount claimed from the answer it is handed.",
        model_answer_inputs=answer_inputs,
    )


def _substitute(reader, inputs, seen):
    def _body(**kwargs):
        seen.append(tuple(sorted(k for k in kwargs if k != "context")))
        return {VALUE_DS: 120}

    return Capacity(
        name="rederive_amount_claimed2",
        category=CATEGORY_COMBINATION,
        inputs=inputs,
        outputs=(VALUE_DS,),
        implementation=_body,
        description="Re-derive the amount claimed without the model.",
        substitute_for=reader.iri,
    )


def _run(reader):
    values = {ANSWER_DS: ANSWER, EXTRA_DS: MATTER, SOURCE_DS: MESSAGE}
    result = execute_pipeline(
        _DirectDispatcher(reader),
        _Pipeline(steps=(_Step(reader.iri, tuple(reader.inputs)),)),
        initial_inputs={ds: values[ds] for ds in reader.inputs},
        request_id="req-answerfed2",
        mm=MentalModel(session_id="s", user_id="u"),
        pipeline_run_ref="pipelinerun:req-answerfed2:1",
    )
    assert result.success is True
    return result.capacity_graph


def _rerun(layer, graph, *, session=None):
    (conclusion,) = identify([graph])
    dispatcher = L4Dispatcher(layer, session=session, kl=KnowledgeLayer.bootstrap(), llm=None)
    return rerun(conclusion, [graph], dispatcher=dispatcher)


def test_a_substitute_for_an_answer_fed_reader_is_handed_the_source_only():
    layer = _layer()
    reader = _reader((ANSWER_DS, SOURCE_DS), (ANSWER_DS,))
    layer.register_capacity(reader)
    seen = []
    layer.register_capacity(_substitute(reader, (SOURCE_DS,), seen))

    (run,) = _rerun(layer, _run(reader)).runs

    assert (run.agrees, run.value, run.failure) == (True, 120, None)
    assert seen == [(SOURCE_DS,)]


def test_a_substitute_that_no_longer_pairs_after_the_reader_is_redeclared_is_not_run():
    layer = _layer()
    reader = _reader((ANSWER_DS, EXTRA_DS, SOURCE_DS), (ANSWER_DS,))
    layer.register_capacity(reader)
    seen = []
    layer.register_capacity(_substitute(reader, (EXTRA_DS, SOURCE_DS), seen))
    redeclared = _reader((ANSWER_DS, EXTRA_DS, SOURCE_DS), (ANSWER_DS, EXTRA_DS))
    layer.register_capacity(redeclared, if_exists="upsert")

    report = _rerun(layer, _run(redeclared))

    (run,) = report.runs
    assert report.excisable is True
    assert (run.agrees, run.failure) == (None, NO_LONGER_PAIRS)
    assert seen == []


def test_the_pairing_is_checked_against_the_reader_in_the_reruns_own_scope():
    layer = _layer()
    reader = _reader((ANSWER_DS, EXTRA_DS, SOURCE_DS), (ANSWER_DS,))
    layer.register_capacity(reader)
    seen = []
    layer.register_capacity(_substitute(reader, (EXTRA_DS, SOURCE_DS), seen))
    alice = build_session("alice")
    shadow = _reader((ANSWER_DS, EXTRA_DS, SOURCE_DS), (ANSWER_DS, EXTRA_DS))
    layer.register_capacity(shadow, session=alice)
    graph = _run(shadow)

    (hers,) = _rerun(layer, graph, session=alice).runs
    assert (hers.agrees, hers.failure) == (None, NO_LONGER_PAIRS)
    assert seen == []

    (shared,) = _rerun(layer, graph).runs
    assert (shared.agrees, shared.failure) == (True, None)
    assert seen == [(EXTRA_DS, SOURCE_DS)]
