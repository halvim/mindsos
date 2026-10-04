"""An ANSWER-FED reader can be paired with a substitute (plan item I-18).

``docs/plans/MINDSOS_LLM_PLAN.md`` ruling R44 (OWNER 2026-10-03, amends R37);
ADR-0210 amendment 8. A reader is a capacity that CALLS the model, or one
that DECLARES which of its inputs carry the model's answer. For the second
kind the substitute takes the reader's inputs MINUS the answer: a substitute
handed the answer would not be re-deriving without the model.

The rule is ``admission.substitute_problems``, a function over plain values,
so it is exercised here on declarations alone.
"""

from __future__ import annotations

from types import SimpleNamespace

from mindsos_capacity.admission import substitute_problems

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
