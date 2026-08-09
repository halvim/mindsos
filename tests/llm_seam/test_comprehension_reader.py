"""The comprehension reader — what it admits, and what it refuses.

The load-bearing case is :func:`test_a_quote_absent_from_the_source_is_refused`:
a value the model reports but cannot quote from the document is refused, not
flagged. That is what turns a fabricated reading into a refusal by
construction instead of a monitoring problem.

Close behind it is :func:`test_a_value_that_will_not_fit_its_shape_is_refused`.
An uncoerced reading would hand a *threshold* the string ``"about seven
weeks"`` to compare against ``30`` — a confidently wrong answer, which is the
one failure the product cannot have.
"""

from __future__ import annotations

import pytest

from mindsos_capacity.builtins.comprehension_v0 import (
    build_reader,
    coerce_to_shape,
    locate_quote,
)
from mindsos_capacity.builtins.origin_v0 import (
    BASIS_STATED,
    ORIGIN_READ_BY_MODEL,
    PRODUCER_DOCUMENT_READING,
    REFUSAL_FIELD_ABSENT,
    REFUSAL_MODEL_DECLINED,
    REFUSAL_MODEL_UNREACHABLE,
    REFUSAL_QUOTE_NOT_IN_SOURCE,
    REFUSAL_VALUE_NOT_COERCIBLE,
    missing_declared_fields,
    origin_record_iri,
)
from mindsos_capacity.datastate import ShapeDescriptor
from mindsos_capacity.exceptions import CapacityRegistrationError
from mindsos_capacity.family_rules import FamilyDontKnowShape, family_rule_for
from mindsos_capacity.identifiers import datastate_iri

SOURCE_DS = datastate_iri("claims.submission_email")
VALUE_DS = datastate_iri("claims.elapsed_days")
RECORD_DS = origin_record_iri(VALUE_DS)

EMAIL = (
    "Order 4471. I purchased the item on 3 March 2026 and\n"
    "claimed 47 days later. I was in hospital after the operation."
)

QUESTION = "how many days elapsed between purchase and claim"


class _LLM:
    def __init__(self, payload, raises=None):
        self.payload = payload
        self.raises = raises
        self.calls = []

    def read(self, **kwargs):
        self.calls.append(kwargs)
        if self.raises is not None:
            raise self.raises
        return dict(self.payload)


class _Ctx:
    def __init__(self, llm):
        self.llm = llm


def _reader(**over):
    kwargs = dict(
        name="read_elapsed_days",
        source_datastate_iri=SOURCE_DS,
        value_datastate_iri=VALUE_DS,
        prompt_iri="prompt:claims.elapsed_days",
        prompt_version=4,
        field_name="elapsed_days",
        question=QUESTION,
        description="Read the elapsed days from the submission.",
        origin_party_phrase="the customer",
        source_identity_phrase="their submission email",
        expected_basis=BASIS_STATED,
        value_shape=ShapeDescriptor.scalar("int", opaque_tag="claims.elapsed_days"),
    )
    kwargs.update(over)
    return build_reader(**kwargs)


def _run(payload, raises=None):
    llm = _LLM(payload, raises)
    return _reader().implementation(**{SOURCE_DS: EMAIL, "context": _Ctx(llm)}), llm


ADMITTED = {
    "fields": [{"name": "elapsed_days", "value": "47",
                "quote": "claimed 47 days later", "basis": BASIS_STATED}],
    "model_id": "model-x", "model_version": "2026-05-01",
    "prompt_iri": "prompt:claims.elapsed_days", "prompt_version": 4,
    "temperature": 0.0, "request_key": "sha256:abc", "recorded": False,
}


# ── quote location ─────────────────────────────────────────────────────


def test_locate_quote_finds_an_exact_span():
    assert locate_quote("purchased on 3 March", "3 March") == (13, 20)


def test_locate_quote_tolerates_a_line_break_inside_the_quote():
    span = locate_quote(EMAIL, "3 March 2026 and claimed 47 days later")
    assert span is not None
    assert EMAIL[span[0]:span[1]].startswith("3 March")


def test_locate_quote_is_case_sensitive():
    assert locate_quote("purchased on 3 March", "3 march") is None


def test_locate_quote_rejects_words_not_in_the_document():
    assert locate_quote(EMAIL, "claimed 60 days later") is None


# ── coercion ───────────────────────────────────────────────────────────


def test_coercion_fits_the_declared_shape():
    assert coerce_to_shape("47", ShapeDescriptor.scalar("int")) == 47
    assert coerce_to_shape("2.5", ShapeDescriptor.scalar("float")) == 2.5
    assert coerce_to_shape("yes", ShapeDescriptor.scalar("bool")) is True


def test_an_opaque_shape_declares_there_is_nothing_to_check():
    # Honest, and the hazard the registry walk exists to catch.
    assert coerce_to_shape("about seven weeks", ShapeDescriptor.opaque("x")) == "about seven weeks"


# ── admitted reading ───────────────────────────────────────────────────


def test_an_admitted_reading_is_typed_and_carries_its_provenance():
    out, llm = _run(ADMITTED)
    assert out[VALUE_DS] == 47 and isinstance(out[VALUE_DS], int)

    record = out[RECORD_DS]
    assert record["admitted"] is True
    assert record["origin_producer_kind"] == PRODUCER_DOCUMENT_READING
    assert record["origin_method"] == ORIGIN_READ_BY_MODEL
    assert record["origin_method_phrase"] == "read by a language model"
    assert record["quote_verified"] is True
    start, end = record["quote_offsets"]
    assert EMAIL[start:end] == record["quote"]
    assert record["basis"] == BASIS_STATED
    assert record["expected_basis"] == BASIS_STATED
    assert record["model_id"] == "model-x"
    assert record["prompt_version"] == 4
    assert record["recorded"] is False
    assert llm.calls[0]["prompt_iri"] == "prompt:claims.elapsed_days"


def test_the_two_phrases_stay_separate():
    # One welded string could not serve a producer that consults an
    # authority and has no asserting party.
    record, _ = _run(ADMITTED)
    record = record[RECORD_DS]
    assert record["origin_party_phrase"] == "the customer"
    assert record["source_identity_phrase"] == "their submission email"


def test_a_reader_supplies_everything_it_declared():
    record, _ = _run(ADMITTED)
    assert missing_declared_fields(record[RECORD_DS]) == []


def test_printed_phrases_carry_no_identifiers():
    record, _ = _run(ADMITTED)
    record = record[RECORD_DS]
    for key in ("question", "origin_party_phrase", "source_identity_phrase",
                "origin_method_phrase"):
        assert ":" not in record[key], key


# ── refusals ───────────────────────────────────────────────────────────


def test_a_quote_absent_from_the_source_is_refused():
    out, _ = _run({"fields": [{"name": "elapsed_days", "value": "47",
                               "quote": "claimed 60 days later", "basis": BASIS_STATED}]})
    assert out[VALUE_DS] is None
    record = out[RECORD_DS]
    assert record["refusal_reason"] == REFUSAL_QUOTE_NOT_IN_SOURCE
    assert record["claimed_quote"] == "claimed 60 days later"
    assert record["environment_fault"] is False


def test_a_value_that_will_not_fit_its_shape_is_refused():
    out, _ = _run({"fields": [{"name": "elapsed_days", "value": "about seven weeks",
                               "quote": "claimed 47 days later", "basis": BASIS_STATED}]})
    assert out[VALUE_DS] is None
    record = out[RECORD_DS]
    assert record["refusal_reason"] == REFUSAL_VALUE_NOT_COERCIBLE
    # The quote that produced the unusable value is kept beside the refusal.
    assert record["quote_verified"] is True
    assert record["quote"] == "claimed 47 days later"


def test_a_model_decline_is_refused_with_its_reason():
    out, _ = _run({"declined": True, "decline_reason": "the email does not say"})
    assert out[RECORD_DS]["refusal_reason"] == REFUSAL_MODEL_DECLINED
    assert "does not say" in out[RECORD_DS]["refusal_detail"]


def test_a_missing_field_is_refused():
    out, _ = _run({"fields": [{"name": "something_else", "value": 1, "quote": "sorry"}]})
    assert out[RECORD_DS]["refusal_reason"] == REFUSAL_FIELD_ABSENT


def test_a_transport_failure_is_a_refusal_flagged_as_ours():
    # A run that dies on venue wifi must still leave something renderable —
    # and it must never pad the customer's refusal list.
    out, _ = _run(None, raises=ConnectionError("connection reset"))
    assert out[VALUE_DS] is None
    record = out[RECORD_DS]
    assert record["refusal_reason"] == REFUSAL_MODEL_UNREACHABLE
    assert record["environment_fault"] is True


def test_budget_and_replay_miss_still_raise():
    # Run-level policy and a fault in our recorded set: a batch stopping
    # loudly beats 300 Records blaming the customer's documents.
    class LLMCallBudgetExceeded(Exception): pass
    class RecordedResponseMiss(Exception): pass

    for exc in (LLMCallBudgetExceeded("ceiling"), RecordedResponseMiss("miss")):
        with pytest.raises(type(exc)):
            _run(None, raises=exc)


def test_a_refusal_keeps_every_registered_fact():
    out, _ = _run({"declined": True, "decline_reason": "nothing to read"})
    record = out[RECORD_DS]
    assert record["question"] == QUESTION
    assert record["expected_basis"] == BASIS_STATED
    assert record["origin_party_phrase"] == "the customer"
    assert record["source_identity_phrase"] == "their submission email"
    # Observed facts are absent entirely, not present-and-null: they are
    # outside READER_SUPPLIED_FIELDS, so absence here is normal and the
    # renderer reads them with .get() rather than inferring from a key.
    assert record.get("basis") is None
    assert record.get("quote") is None


def test_no_llm_on_the_context_is_an_error_not_a_dont_know():
    with pytest.raises(CapacityRegistrationError):
        _reader().implementation(**{SOURCE_DS: EMAIL, "context": _Ctx(None)})


# ── declaration + family contract ──────────────────────────────────────


def test_a_reader_declares_two_outputs_in_the_llm_category():
    from mindsos_intelligence.dispatch import LLM_CATEGORIES

    reader = _reader()
    assert reader.category in LLM_CATEGORIES
    assert not hasattr(reader, "consults_llm")
    assert reader.outputs == (VALUE_DS, RECORD_DS)


def test_comprehension_dont_know_shape_is_optional_return():
    assert family_rule_for(_reader().iri) is FamilyDontKnowShape.OPTIONAL_RETURN


def test_origin_record_type_is_per_value_and_single_dot():
    assert origin_record_iri(VALUE_DS) != origin_record_iri(datastate_iri("a.other"))
    assert origin_record_iri(VALUE_DS).split(":", 1)[-1].count(".") == 1


def test_an_identifier_shaped_phrase_is_refused_at_registration():
    with pytest.raises(Exception):
        _reader(origin_party_phrase="datastate:party.customer")
    with pytest.raises(Exception):
        _reader(source_identity_phrase="datastate:claims.email")
