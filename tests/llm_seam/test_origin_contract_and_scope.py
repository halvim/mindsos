"""The origin contract, and the guards that must follow scope.

Two things are pinned here that would otherwise fail silently:

* **A guard that reads only Global stops working the moment registration
  moves Local** — which is exactly the configuration a Local-first trial
  chooses. Every guard in ``origin_v0`` is scope-aware, and these tests
  fail if that regresses.
* **The union is closed by agreement.** A producer inventing a field is
  refused at build time, because two producers is where invention starts
  and the renderer would be reading a field nobody declared.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins import origin_v0 as origin
from mindsos_capacity.builtins.comprehension_v0 import register_reader
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.exceptions import CapacityRegistrationError
from mindsos_capacity.identifiers import (
    CATEGORY_COMPREHENSION,
    CATEGORY_DECISION,
    datastate_iri,
)

SOURCE_DS = datastate_iri("claims.submission_email")
OUTCOME_DS = datastate_iri("claims.window_outcome")
DAYS_DS = datastate_iri("claims.elapsed_days")


class _Session:
    def __init__(self, user_id):
        self.user_id = user_id
        self.session_id = "s"

    def has(self, _capability):  # pragma: no cover — Local needs none
        return True


def _layer():
    return CapacityLayer()


def _register_datastate(layer, iri, kind, session=None):
    shape = (
        ShapeDescriptor.opaque(iri)
        if kind == "opaque"
        else ShapeDescriptor.scalar(kind, opaque_tag=iri)
    )
    layer.register_datastate(
        DataState(name=iri.split(":", 1)[-1], shape=shape, description="d",
                  provenance_category=CATEGORY_COMPREHENSION),
        session=session, allow_new_realm=True,
    )


def _register_decision(layer, *, inputs=(), outputs=(), session=None, name="assess_window"):
    layer.register_capacity(
        Capacity(name=name, category=CATEGORY_DECISION, inputs=tuple(inputs),
                 outputs=tuple(outputs), implementation=lambda **kw: {},
                 description="Decide."),
        session=session,
    )


# ── the union ──────────────────────────────────────────────────────────


def test_the_spine_is_written_by_every_producer():
    record = origin.build_origin_record(
        producer_kind=origin.PRODUCER_POLICY_LOOKUP,
        origin_method=origin.ORIGIN_READ_FROM_SOURCE,
        source_identity_phrase="the claims policy",
        source_datastate=datastate_iri("claims.policy_id"),
        question="the maximum days allowed between purchase and claim",
        admitted=True,
        supplied_fields=[origin.FIELD_SOURCE_VERSION, origin.FIELD_SOURCE_IN_FORCE_FROM],
        possible_refusal_reasons=[origin.REFUSAL_NO_SOURCE_IN_FORCE,
                                  origin.REFUSAL_SOURCE_UNREACHABLE],
        source_version=4, source_in_force_from="12 March", source_in_force_to="30 June",
    )
    for field in origin.SPINE:
        assert field in record, field


def test_the_money_sentence_assembles_from_the_union_alone():
    # The acceptance test for the whole field set: if the product's headline
    # sentence cannot be composed from the closed union plus the decision's
    # own outputs, the union is wrong however principled it looks.
    record = origin.build_origin_record(
        producer_kind=origin.PRODUCER_POLICY_LOOKUP,
        origin_method=origin.ORIGIN_READ_FROM_SOURCE,
        source_identity_phrase="the claims policy",
        source_datastate=datastate_iri("claims.policy_id"),
        question="the maximum days allowed",
        admitted=True,
        supplied_fields=[origin.FIELD_SOURCE_VERSION, origin.FIELD_SOURCE_IN_FORCE_FROM],
        possible_refusal_reasons=[origin.REFUSAL_NO_SOURCE_IN_FORCE],
        source_version=4, source_in_force_from="12 March",
    )
    sentence = (
        "from {source}, version {version}, in force since {since}".format(
            source=record["source_identity_phrase"],
            version=record["source_version"],
            since=record["source_in_force_from"],
        )
    )
    assert sentence == "from the claims policy, version 4, in force since 12 March"


def test_a_producer_cannot_invent_a_field():
    with pytest.raises(origin.OriginContractError):
        origin.build_origin_record(
            producer_kind=origin.PRODUCER_POLICY_LOOKUP,
            origin_method=origin.ORIGIN_READ_FROM_SOURCE,
            source_identity_phrase="the claims policy", source_datastate=None,
            question="q", admitted=True, supplied_fields=[],
            possible_refusal_reasons=[], confidence_score=0.8,
        )


def test_environment_fault_is_derived_not_passed():
    # A producer must not be able to label its own outage as a finding
    # about the customer's case.
    outage = origin.build_origin_record(
        producer_kind=origin.PRODUCER_DOCUMENT_READING,
        origin_method=origin.ORIGIN_READ_BY_MODEL,
        source_identity_phrase="their submission email", source_datastate=SOURCE_DS,
        question="q", admitted=False, supplied_fields=[],
        possible_refusal_reasons=[origin.REFUSAL_MODEL_UNREACHABLE],
        refusal_reason=origin.REFUSAL_MODEL_UNREACHABLE, refusal_detail="timeout",
    )
    finding = origin.build_origin_record(
        producer_kind=origin.PRODUCER_DOCUMENT_READING,
        origin_method=origin.ORIGIN_READ_BY_MODEL,
        source_identity_phrase="their submission email", source_datastate=SOURCE_DS,
        question="q", admitted=False, supplied_fields=[],
        possible_refusal_reasons=[origin.REFUSAL_QUOTE_NOT_IN_SOURCE],
        refusal_reason=origin.REFUSAL_QUOTE_NOT_IN_SOURCE, refusal_detail="not there",
    )
    assert outage["environment_fault"] is True
    assert finding["environment_fault"] is False


def test_a_producer_cannot_emit_a_reason_it_did_not_declare():
    # The renderer must be able to tell "a lookup would never say
    # quote_not_found_in_source" from "this lookup happened not to".
    with pytest.raises(origin.OriginContractError):
        origin.build_origin_record(
            producer_kind=origin.PRODUCER_POLICY_LOOKUP,
            origin_method=origin.ORIGIN_READ_FROM_SOURCE,
            source_identity_phrase="the claims policy", source_datastate=None,
            question="q", admitted=False, supplied_fields=[],
            possible_refusal_reasons=[origin.REFUSAL_NO_SOURCE_IN_FORCE],
            refusal_reason=origin.REFUSAL_QUOTE_NOT_IN_SOURCE, refusal_detail="x",
        )


def test_a_store_outage_is_an_environment_fault_a_missing_edition_is_not():
    # "No policy in force at that date" is a finding about the customer's
    # case and belongs in their refusal list; "our store was down" does not.
    def _mk(reason):
        return origin.build_origin_record(
            producer_kind=origin.PRODUCER_POLICY_LOOKUP,
            origin_method=origin.ORIGIN_READ_FROM_SOURCE,
            source_identity_phrase="the claims policy", source_datastate=None,
            question="q", admitted=False, supplied_fields=[],
            possible_refusal_reasons=[origin.REFUSAL_NO_SOURCE_IN_FORCE,
                                      origin.REFUSAL_SOURCE_UNREACHABLE],
            refusal_reason=reason, refusal_detail="d",
        )
    assert _mk(origin.REFUSAL_NO_SOURCE_IN_FORCE)["environment_fault"] is False
    assert _mk(origin.REFUSAL_SOURCE_UNREACHABLE)["environment_fault"] is True


def test_a_promised_field_left_empty_is_a_defect():
    record = origin.build_origin_record(
        producer_kind=origin.PRODUCER_DOCUMENT_READING,
        origin_method=origin.ORIGIN_READ_BY_MODEL,
        source_identity_phrase="their submission email", source_datastate=SOURCE_DS,
        question="q", admitted=True, supplied_fields=[origin.FIELD_QUOTE],
        possible_refusal_reasons=[],
    )
    assert origin.missing_declared_fields(record) == [origin.FIELD_QUOTE]


# ── guards follow the scope ────────────────────────────────────────────


def test_the_no_decide_guard_sees_a_local_decision_capacity():
    # The regression that would matter most: register everything Local and
    # a Global-only guard finds nothing to object to.
    layer = _layer()
    session = _Session("dr-user")
    _register_datastate(layer, SOURCE_DS, "str", session=session)
    _register_datastate(layer, OUTCOME_DS, "str", session=session)
    _register_decision(layer, outputs=(OUTCOME_DS,), session=session)

    with pytest.raises(CapacityRegistrationError) as excinfo:
        register_reader(
            layer, name="read_outcome", source_datastate_iri=SOURCE_DS,
            value_datastate_iri=OUTCOME_DS, value_description="The outcome.",
            prompt_iri="p", prompt_version=1, field_name="outcome",
            question="what the outcome should be", description="Read the outcome.",
            origin_party_phrase="the customer",
            source_identity_phrase="their submission email",
            expected_basis=origin.BASIS_STATED, session=session,
        )
    assert "may not produce a decision" in str(excinfo.value)


def test_a_local_reader_registers_into_the_local_metagraph_only():
    layer = _layer()
    session = _Session("dr-user")
    _register_datastate(layer, SOURCE_DS, "str", session=session)
    reader = register_reader(
        layer, name="read_days", source_datastate_iri=SOURCE_DS,
        value_datastate_iri=DAYS_DS, value_description="Elapsed days.",
        prompt_iri="p", prompt_version=1, field_name="elapsed_days",
        question="how many days elapsed", description="Read elapsed days.",
        origin_party_phrase="the customer",
        source_identity_phrase="their submission email",
        expected_basis=origin.BASIS_STATED,
        value_shape=ShapeDescriptor.scalar("int", opaque_tag=DAYS_DS),
        session=session,
    )
    local = layer.local_metagraph("dr-user").metagraph_id
    glob = layer.global_metagraph().metagraph_id
    assert reader.iri in layer._capacity_index[local]
    assert reader.iri not in layer._capacity_index.get(glob, {})


def test_the_opaque_into_decision_walk_finds_a_local_pairing():
    layer = _layer()
    session = _Session("dr-user")
    _register_datastate(layer, DAYS_DS, "opaque", session=session)
    _register_decision(layer, inputs=(DAYS_DS,), session=session, name="threshold_window")

    assert origin.opaque_into_decision(layer, user_id="dr-user") == [
        (DAYS_DS, "capacity:decision:threshold_window")
    ]
    # A Global-only walk sees nothing — which is the silent failure.
    assert origin.opaque_into_decision(layer) == []


def test_a_shaped_value_into_a_decision_is_not_flagged():
    layer = _layer()
    session = _Session("dr-user")
    _register_datastate(layer, DAYS_DS, "int", session=session)
    _register_decision(layer, inputs=(DAYS_DS,), session=session, name="threshold_window")
    assert origin.opaque_into_decision(layer, user_id="dr-user") == []
