"""The structured-ingest reader — the producer that does not use a model.

**Why it exists.** Claim 5 of the demo plan is *the model reads, it does not
decide*, shown by running the same cases twice — structured, then read — and
getting identical answers with different origins. This is the structured half,
so it is a control arm rather than scaffolding.

**What it replaced.** A stand-in that stamped ``origin_method=read_by_model``
on every record while no model existed anywhere in the system. That put false
provenance on three of the five runs, in the product whose whole claim is
provenance, and it was found by rendering a graph rather than by reading code.
"""

from __future__ import annotations

import pytest

from mindsos_capacity.builtins.origin_v0 import (
    FIELD_ADMITTED,
    FIELD_BASIS,
    FIELD_POSSIBLE_REFUSAL_REASONS,
    FIELD_PRODUCER_KIND,
    FIELD_QUESTION,
    FIELD_REFUSAL_REASON,
    FIELD_SOURCE_IDENTITY_PHRASE,
    ORIGIN_READ_BY_MODEL,
    ORIGIN_READ_FROM_SOURCE,
    ORIGIN_SHAPE_TAG,
    OriginContractError,
    PRODUCER_STRUCTURED_INGEST,
    REFUSAL_FIELD_ABSENT,
    REFUSAL_VALUE_NOT_COERCIBLE,
    missing_declared_fields,
)
from mindsos_capacity.builtins.structured_ingest_v0 import (
    CATEGORY,
    StructuredSourceUnreadableError,
    build_structured_ingest_reader,
    structured_value_datastates,
)
from mindsos_capacity.family_rules import FamilyDontKnowShape
from mindsos_capacity import family_rule_for

from ._dr_fixtures import (
    DS_FILING_RECORD,
    DS_GROSS_INCOME,
    DS_GROSS_INCOME_ORIGIN,
    INCOME_FIELD,
    reader_declaration,
)


def _run(source):
    return reader_declaration().implementation(**{DS_FILING_RECORD: source})


# ── the contract ──────────────────────────────────────────────────────


def test_the_reader_declares_the_value_and_its_origin_as_outputs():
    d = reader_declaration()
    assert d.outputs == (DS_GROSS_INCOME, DS_GROSS_INCOME_ORIGIN)
    assert d.inputs == (DS_FILING_RECORD,)


def test_the_reader_is_retrieval_and_gets_the_optional_return_contract():
    """A reader that may find nothing needs OPTIONAL_RETURN — ADR-0208 D1's
    argument, applied to the second producer. ``comprehension`` would file the
    one producer that provably uses no model under a reading family."""
    assert reader_declaration().category == CATEGORY == "retrieval"
    assert family_rule_for(reader_declaration().iri) is FamilyDontKnowShape.OPTIONAL_RETURN


def test_the_value_carries_a_real_shape_and_never_an_opaque_one():
    value, origin = structured_value_datastates(
        value_name="dr.probe_value", value_elem="int",
        value_description="a number somebody stated",
    )
    assert value.shape.to_dict() == {"kind": "scalar", "elem": "int"}
    assert origin.shape.to_dict() == {"kind": "opaque", "opaque_tag": ORIGIN_SHAPE_TAG}


def test_both_producers_tag_their_origin_records_identically():
    """One tag, or a renderer can no longer treat 'the origin of this value'
    as one thing. This is why ORIGIN_SHAPE_TAG moved into origin_v0."""
    from mindsos_capacity.builtins.policy_lookup_v0 import policy_limit_datastates
    _, lookup_origin = policy_limit_datastates(
        limit_name="dr.probe_limit", limit_elem="int",
        limit_description="a limit somebody published",
    )
    _, ingest_origin = structured_value_datastates(
        value_name="dr.probe_value", value_elem="int",
        value_description="a number somebody stated",
    )
    assert lookup_origin.shape == ingest_origin.shape


# ── it admits ─────────────────────────────────────────────────────────


def test_a_stated_value_is_read_and_attributed_to_the_source():
    out = _run({INCOME_FIELD: 61000})
    assert out[DS_GROSS_INCOME] == 61000
    rec = out[DS_GROSS_INCOME_ORIGIN]
    assert rec[FIELD_PRODUCER_KIND] == PRODUCER_STRUCTURED_INGEST
    assert rec[FIELD_ADMITTED] is True
    assert rec[FIELD_SOURCE_IDENTITY_PHRASE] == "their filed return"
    assert rec[FIELD_BASIS] == "stated"
    assert missing_declared_fields(rec) == []


def test_no_record_this_producer_writes_ever_claims_a_model_read_it():
    """The defect this module exists to remove, asserted as a behaviour so it
    cannot come back by a copied line."""
    for source in ({INCOME_FIELD: 61000}, {}, {INCOME_FIELD: "not stated"}):
        rec = _run(source)[DS_GROSS_INCOME_ORIGIN]
        assert rec["origin_method"] == ORIGIN_READ_FROM_SOURCE
        assert rec["origin_method"] != ORIGIN_READ_BY_MODEL
        assert "model" not in rec["origin_method_phrase"]


def test_a_string_that_is_a_number_is_read_rather_than_refused():
    assert _run({INCOME_FIELD: "61000"})[DS_GROSS_INCOME] == 61000


# ── it refuses, twice, differently ────────────────────────────────────


def test_an_absent_field_refuses_and_names_the_source_in_prose():
    out = _run({})
    assert out[DS_GROSS_INCOME] is None
    rec = out[DS_GROSS_INCOME_ORIGIN]
    assert rec[FIELD_REFUSAL_REASON] == REFUSAL_FIELD_ABSENT
    assert rec[FIELD_ADMITTED] is False
    assert "their filed return" in rec["refusal_detail"]


def test_a_value_that_is_not_a_number_is_a_different_refusal():
    """*They did not state it* and *they stated something that is not a
    number* are different facts about the customer's material. A Record that
    reported one as the other would be false."""
    rec = _run({INCOME_FIELD: "not stated"})[DS_GROSS_INCOME_ORIGIN]
    assert rec[FIELD_REFUSAL_REASON] == REFUSAL_VALUE_NOT_COERCIBLE
    assert rec[FIELD_REFUSAL_REASON] != REFUSAL_FIELD_ABSENT


def test_both_reasons_are_declared_on_every_record_admitted_or_not():
    for source in ({INCOME_FIELD: 61000}, {}):
        rec = _run(source)[DS_GROSS_INCOME_ORIGIN]
        assert set(rec[FIELD_POSSIBLE_REFUSAL_REASONS]) == {
            REFUSAL_FIELD_ABSENT, REFUSAL_VALUE_NOT_COERCIBLE
        }


def test_a_source_that_is_not_a_record_raises_rather_than_blaming_the_case():
    """Our wiring defect, so it is reported the way an outage is — by L-2's
    terminal node — never written into a record as though the material were at
    fault. Same split as policy_lookup_v0's source_unreachable."""
    with pytest.raises(StructuredSourceUnreadableError) as excinfo:
        _run("gross income of 61,000 for tax year 2024")
    text = str(excinfo.value)
    assert "their filed return" in text
    assert "fault on our side" in text
    assert ":" not in text


# ── registration-time guards ──────────────────────────────────────────


def test_a_description_naming_its_own_datastate_is_refused():
    with pytest.raises(OriginContractError):
        structured_value_datastates(
            value_name="dr.gross_income", value_elem="int",
            value_description="where dr.gross_income came from",
        )


def test_an_opaque_element_type_is_refused():
    with pytest.raises(OriginContractError):
        structured_value_datastates(
            value_name="dr.probe_value", value_elem="opaque",
            value_description="a number somebody stated",
        )


def test_an_identifier_in_a_printed_phrase_is_refused_at_build_time():
    with pytest.raises(OriginContractError):
        build_structured_ingest_reader(
            name="probe", field="x",
            value_datastate_iri="datastate:dr.probe_value", value_elem="int",
            source_datastate_iri=DS_FILING_RECORD,
            source_identity_phrase="datastate:dr.filing_record",
            question="What does it state?",
        )
