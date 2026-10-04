"""Excision gate 3 — a SUBSTITUTE is declared, paired, and never planned.

Plan item I-12 (``docs/plans/MINDSOS_LLM_PLAN.md``), ruling R37 (OWNER
2026-09-29); ADR-0210 amendment 7 clause 13. A capacity that re-derives a
model reader's conclusion without the model declares
``substitute_for=<reader IRI>``:

* the finders never admit it — they take the first producer of a DataState
  by sorted IRI, and this file's substitute sorts BEFORE its reader
  (``combination`` < ``comprehension``), so admitting it would silently swap
  it in for the reader in ordinary runs;
* registration refuses a pairing that is not a substitute: an unregistered
  reader, a reader that neither consults the model nor declares the input
  carrying its answer (R44), a substitute that consults it, different inputs,
  or outputs the reader does not produce.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import Capacity, CapacityLayer, CapacityRegistrationError
from mindsos_capacity.admission import declaration_refusals
from mindsos_capacity.builtins import origin_v0 as origin
from mindsos_capacity.builtins.comprehension_v0 import register_reader
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_COMBINATION,
    CATEGORY_COMPREHENSION,
    datastate_iri,
)
from mindsos_capacity.pipeline import ConjunctionFinder

SOURCE_DS = datastate_iri("excise3.submission")
DAYS_DS = datastate_iri("excise3.days_waited")
OTHER_DS = datastate_iri("excise3.other")


def _register_datastate(layer, iri, kind):
    shape = (
        ShapeDescriptor.opaque(iri)
        if kind == "opaque"
        else ShapeDescriptor.scalar(kind, opaque_tag=iri)
    )
    layer.register_datastate(
        DataState(name=iri.split(":", 1)[-1], shape=shape, description="d",
                  provenance_category=CATEGORY_COMPREHENSION),
        allow_new_realm=True,
    )


def _layer_with_reader():
    layer = CapacityLayer()
    _register_datastate(layer, SOURCE_DS, "str")
    _register_datastate(layer, OTHER_DS, "opaque")
    reader = register_reader(
        layer, name="read_days", source_datastate_iri=SOURCE_DS,
        value_datastate_iri=DAYS_DS, value_description="Days waited.",
        prompt_iri="prompt:excise3.days", prompt_version=1,
        field_name="days", question="how many days the customer waited",
        description="Read the days waited.",
        origin_party_phrase="the customer",
        source_identity_phrase="their submission",
        expected_basis=origin.BASIS_STATED,
        value_shape=ShapeDescriptor.scalar("int", opaque_tag=DAYS_DS),
    )
    return layer, reader


def _substitute(substitute_for, *, inputs=(SOURCE_DS,), outputs=(DAYS_DS,), consults_llm=False, name="rederive_days"):
    return Capacity(
        name=name,
        category=CATEGORY_COMBINATION,
        inputs=inputs,
        outputs=outputs,
        implementation=lambda **kw: {DAYS_DS: 7},
        description="Re-derive the days waited without the model.",
        consults_llm=consults_llm,
        substitute_for=substitute_for,
    )


def test_a_substitute_is_registered_against_its_reader():
    layer, reader = _layer_with_reader()
    sub = _substitute(reader.iri)

    layer.register_capacity(sub)

    assert layer.resolve_declaration(sub.iri).substitute_for == reader.iri
    assert sub.iri < reader.iri, "the premise: the substitute sorts first"


def test_the_refusal_map_names_a_substitute():
    layer, reader = _layer_with_reader()
    sub = _substitute(reader.iri)
    layer.register_capacity(sub)

    refused = declaration_refusals(layer, layer.global_view())

    assert refused.get(sub.iri) == (SOURCE_DS,)
    assert reader.iri not in refused


def test_the_finder_routes_through_the_reader_not_the_substitute():
    layer, reader = _layer_with_reader()
    layer.register_capacity(_substitute(reader.iri))

    verdict = ConjunctionFinder().find(
        layer, start_datastates=(SOURCE_DS,), target_datastate=DAYS_DS
    )

    assert verdict.found
    assert [s.capacity_iri for s in verdict.pipeline.steps] == [reader.iri]


def test_a_substitute_for_an_unregistered_reader_is_refused():
    layer, _ = _layer_with_reader()

    with pytest.raises(CapacityRegistrationError, match="not registered"):
        layer.register_capacity(_substitute("capacity:comprehension:no_such_reader"))


def test_a_substitute_that_consults_the_model_is_refused():
    layer, reader = _layer_with_reader()

    with pytest.raises(CapacityRegistrationError, match="consults_llm=True"):
        layer.register_capacity(_substitute(reader.iri, consults_llm=True))


def test_a_substitute_with_other_inputs_is_refused():
    layer, reader = _layer_with_reader()

    with pytest.raises(CapacityRegistrationError, match="its inputs"):
        layer.register_capacity(_substitute(reader.iri, inputs=(SOURCE_DS, OTHER_DS)))


def test_a_substitute_producing_what_the_reader_does_not_is_refused():
    layer, reader = _layer_with_reader()

    with pytest.raises(CapacityRegistrationError, match="its outputs"):
        layer.register_capacity(_substitute(reader.iri, outputs=(OTHER_DS,)))


def test_a_substitute_for_a_capacity_that_does_not_consult_the_model_is_refused():
    layer, reader = _layer_with_reader()
    plain = _substitute(None, name="plain_days")
    layer.register_capacity(plain)

    with pytest.raises(CapacityRegistrationError, match="neither consults the borrowed model"):
        layer.register_capacity(_substitute(plain.iri, name="rederive_plain"))
