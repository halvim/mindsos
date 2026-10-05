"""An ANSWER-FED reader can be paired with a substitute (plan item I-18).

``docs/plans/MINDSOS_LLM_PLAN.md`` ruling R44 (OWNER 2026-10-03, amends R37);
ADR-0210 amendment 8. A reader is a capacity that CALLS the model, or one
that DECLARES which of its inputs carry the model's answer. For the second
kind the substitute takes the reader's inputs MINUS the answer: a substitute
handed the answer would not be re-deriving without the model.

The rule is ``admission.substitute_problems``, a function over plain values,
so it is exercised here on declarations alone; the second half of the file
shows registration applying it, and refusing a declaration that is not the
capacity's own (``admission.answer_input_problems``).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mindsos_capacity import Capacity, CapacityLayer, CapacityRegistrationError
from mindsos_capacity.admission import substitute_problems
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import CATEGORY_COMBINATION, CATEGORY_COMPREHENSION

ANSWER = "datastate:answerfed.model_answer"
SOURCE = "datastate:answerfed.message"
VALUE = "datastate:answerfed.amount_claimed"
RECORD = VALUE + "_origin"


def _declaration(*, inputs, outputs, consults_llm=False, model_answer_inputs=()):
    return SimpleNamespace(
        inputs=inputs,
        outputs=outputs,
        consults_llm=consults_llm,
        model_answer_inputs=model_answer_inputs,
    )


def _answer_fed_reader():
    return _declaration(
        inputs=(ANSWER, SOURCE),
        outputs=(VALUE, RECORD),
        model_answer_inputs=(ANSWER,),
    )


def test_a_substitute_taking_the_source_only_pairs_with_an_answer_fed_reader():
    substitute = _declaration(inputs=(SOURCE,), outputs=(VALUE,))

    assert substitute_problems(substitute, _answer_fed_reader()) == ()


def test_a_substitute_handed_the_answer_is_refused():
    substitute = _declaration(inputs=(ANSWER, SOURCE), outputs=(VALUE,))

    problems = substitute_problems(substitute, _answer_fed_reader())

    assert [p for p in problems if p.startswith("its inputs")], problems


def test_a_capacity_that_neither_consults_nor_declares_cannot_be_substituted():
    plain = _declaration(inputs=(ANSWER, SOURCE), outputs=(VALUE, RECORD))
    substitute = _declaration(inputs=(SOURCE,), outputs=(VALUE,))

    assert substitute_problems(substitute, plain) != ()


def test_a_reader_handed_only_the_answer_leaves_no_source_to_rederive_from():
    reader = _declaration(
        inputs=(ANSWER,), outputs=(VALUE, RECORD), model_answer_inputs=(ANSWER,)
    )
    substitute = _declaration(inputs=(), outputs=(VALUE,))

    problems = substitute_problems(substitute, reader)

    assert [p for p in problems if "no input left" in p], problems


def _layer():
    layer = CapacityLayer()
    for iri in (ANSWER, SOURCE, VALUE, RECORD):
        name = iri.split(":", 1)[-1]
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description="d",
                provenance_category=CATEGORY_COMPREHENSION,
            ),
            allow_new_realm=True,
        )
    return layer


def _reader(**overrides):
    fields = dict(
        name="mint_amount_claimed",
        category=CATEGORY_COMPREHENSION,
        inputs=(ANSWER, SOURCE),
        outputs=(VALUE, RECORD),
        implementation=lambda **kw: {VALUE: None, RECORD: {}},
        description="Mint the amount claimed from the answer it is handed.",
        model_answer_inputs=(ANSWER,),
    )
    fields.update(overrides)
    return Capacity(**fields)


def _substitute(reader, **overrides):
    fields = dict(
        name="rederive_amount_claimed",
        category=CATEGORY_COMBINATION,
        inputs=(SOURCE,),
        outputs=(VALUE,),
        implementation=lambda **kw: {VALUE: None},
        description="Re-derive the amount claimed without the model.",
        substitute_for=reader.iri,
    )
    fields.update(overrides)
    return Capacity(**fields)


def test_registration_pairs_a_substitute_with_an_answer_fed_reader():
    layer = _layer()
    reader = _reader()
    layer.register_capacity(reader)
    substitute = _substitute(reader)

    layer.register_capacity(substitute)

    assert [s.iri for s in layer.substitutes_for(reader.iri)] == [substitute.iri]


def test_an_answer_input_that_is_not_the_capacitys_own_input_is_refused():
    layer = _layer()

    with pytest.raises(CapacityRegistrationError, match="not among its inputs"):
        layer.register_capacity(_reader(inputs=(SOURCE,)))


def test_a_capacity_that_calls_the_model_cannot_also_declare_an_answer_input():
    layer = _layer()

    with pytest.raises(CapacityRegistrationError, match="both consults_llm=True and model_answer_inputs"):
        layer.register_capacity(_reader(consults_llm=True))


def test_a_substitute_cannot_declare_an_answer_input():
    layer = _layer()
    reader = _reader()
    layer.register_capacity(reader)

    with pytest.raises(CapacityRegistrationError, match="a substitute is never handed"):
        layer.register_capacity(_substitute(reader, model_answer_inputs=(SOURCE,)))
