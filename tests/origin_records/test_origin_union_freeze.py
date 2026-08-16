"""The origin union is classified, and the classification is checked by running
the producers — ADR-0207 amendment 2.

``origin_v0`` said from the start that the union is *"closed by agreement…
freeze after the second producer proves it."* Three producers shipped and
nobody froze it. A §12 check found the cost: **the system writes 16 of 30
fields**, and one of them can never carry information. Neither fact was visible
anywhere, because an unclassified union cannot distinguish *"nobody has built
that producer yet"* from *"that field is dead"*.

**These tests read the lists and then go and look.** A list that drifts from
what the producers actually emit is a red gate, not a stale comment — which is
the only reason to write the classification down at all.
"""

from __future__ import annotations

import pytest

from mindsos_capacity.builtins import origin_v0 as origin
from mindsos_capacity.builtins.policy_lookup_v0 import (
    PolicyStoreUnreachableError,
    build_policy_limit_lookup,
)
from mindsos_capacity.builtins.comprehension_v0 import build_reader
from mindsos_capacity.builtins.structured_ingest_v0 import (
    build_structured_ingest_reader,
)
from mindsos_capacity.datastate import ShapeDescriptor
from mindsos_capacity.llm import LiveLLM
from mindsos_knowledge.identifiers import ROLE_POLICIES
from mindsos_knowledge.knowledge_layer import KnowledgeLayer
from mindsos_knowledge.policies import write_policy_edition

DS_LIMIT = "datastate:probe.limit"
DS_AS_OF = "datastate:probe.as_of"
DS_RECORD = "datastate:probe.record"
DS_VALUE = "datastate:probe.value"
POLICY = "policy:probe"


class _Ctx:
    def __init__(self, kl=None, llm=None):
        self.kl = kl
        self.llm = llm


def _kl(*editions):
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, ROLE_POLICIES, "global")
    for edition in editions:
        write_policy_edition(handle, policy_id=POLICY, **edition)
    return kl


#: Two editions on purpose. ``source_in_force_to`` is written ONLY when an
#: edition actually has an end date, so a probe using only the open-ended one
#: would classify a live field as reserved. Verified, not assumed.
_CLOSED = dict(version="1.0", in_force_from="2023-01-01", in_force_to="2023-12-31",
               stated_value=10, text="ten")
_OPEN = dict(version="2.0", in_force_from="2024-01-01", in_force_to=None,
             stated_value=20, text="twenty")


DS_DOC = "datastate:probe.document"
DS_DAYS = "datastate:probe.days"
#: Deliberately contains a COLON inside the span a reading quotes. Until
#: 2026-08-16 the leak guard below rejected any printed field containing
#: one, as a proxy for "holds an IRI" — a proxy that was safe only while
#: no producer put verbatim document text on a printed field. The model
#: reader does exactly that, and real documents are full of colons.
DOCUMENT = "Claim summary. Note: filed seven days later, inside the window."
PROMPT = "prompt:probe.read_days"


def _reading_body():
    """One comprehension reader, shaped so every refusal path is reachable:
    a scalar ``int`` value (so a non-numeric answer refuses
    ``value_not_coercible``) read out of a real document (so a fabricated
    quote refuses ``quote_not_found_in_source``)."""
    return build_reader(
        name="probe_reading",
        source_datastate_iri=DS_DOC,
        value_datastate_iri=DS_DAYS,
        prompt_iri=PROMPT,
        prompt_version=1,
        field_name="days",
        question="How many days passed before the claim was filed?",
        description="How many days passed before the claim was filed",
        origin_party_phrase="the customer",
        source_identity_phrase="their submission email",
        expected_basis=origin.BASIS_STATED,
        value_shape=ShapeDescriptor.scalar("int"),
    ).implementation


def _llm(transport):
    """A REAL client over a fake transport — so these paths exercise the
    shipped decode (S-2) rather than a stand-in for it."""
    return LiveLLM(
        transport, model_id="probe-model", model_version="2026-01-01",
    )


def _answer(**field):
    return lambda **_: {"fields": [dict(name="days", **field)]}


def _lookup_body():
    return build_policy_limit_lookup(
        name="probe_lookup", policy_id=POLICY,
        source_identity_phrase="the probe policy",
        question="What did the probe policy state on {as_of}?",
        limit_datastate_iri=DS_LIMIT, as_of_datastate_iri=DS_AS_OF,
    ).implementation


def _reader_body():
    return build_structured_ingest_reader(
        name="probe_reader", field="v",
        value_datastate_iri=DS_VALUE, value_elem="int",
        source_datastate_iri=DS_RECORD,
        source_identity_phrase="the probe record",
        value_phrase="a probe value",
        question="What does the probe record state?",
    ).implementation


def _every_record_the_system_can_write():
    """Every origin record the SHIPPED producers emit, on every path that
    returns one. The raising paths are absent on purpose — a raising step
    writes no record at all, which is the whole reason
    ``environment_fault`` is degenerate."""
    lookup, reader, reading = _lookup_body(), _reader_body(), _reading_body()
    both, open_only = _kl(_CLOSED, _OPEN), _kl(_OPEN)

    def read(transport):
        return reading(context=_Ctx(llm=_llm(transport)), **{DS_DOC: DOCUMENT})

    records = [
        lookup(context=_Ctx(both), **{DS_AS_OF: "2023-06-01"}),      # closed window
        lookup(context=_Ctx(open_only), **{DS_AS_OF: "2024-06-01"}),  # open window
        lookup(context=_Ctx(open_only), **{DS_AS_OF: "1999-01-01"}),  # no edition
        reader(**{DS_RECORD: {"v": 7}}),
        reader(**{DS_RECORD: {}}),
        reader(**{DS_RECORD: {"v": "nope"}}),
        # The model reader, one call per returning path. Its raising paths
        # (an outage, a budget stop, a replay miss, an absent document) are
        # absent on purpose and that is the point of ``model_unreachable``
        # being degenerate: a raising step writes no record at all.
        read(_answer(quote="Note: filed seven days later", value=7,
                     basis=origin.BASIS_STATED)),
        read(lambda **_: {"declined": True, "decline_reason": "the page is illegible"}),
        read(lambda **_: {"fields": [{"name": "something_else"}]}),
        read(_answer(quote="fourteen days later", value=14)),
        read(_answer(quote="Note: filed seven days later", value="about seven weeks")),
        read(lambda **_: "I think it was seven days"),
    ]
    origin_iris = (
        origin.origin_record_iri(DS_LIMIT),
        origin.origin_record_iri(DS_VALUE),
        origin.origin_record_iri(DS_DAYS),
    )
    return [r[i] for r in records for i in origin_iris if i in r]


@pytest.fixture(scope="module")
def emitted():
    records = _every_record_the_system_can_write()
    assert len(records) == 12, "every returning path must yield exactly one record"
    return records


# ── the classification is a partition ─────────────────────────────────


def test_every_field_is_classified_exactly_once():
    written, reserved = set(origin.FIELDS_WRITTEN_TODAY), set(origin.FIELDS_RESERVED)
    assert written | reserved == set(origin.ORIGIN_UNION)
    assert not (written & reserved), "a field cannot be both live and reserved"


def test_a_reserved_field_names_the_producer_that_will_write_it():
    """*"Someone might need it"* is how a union stops meaning anything."""
    for field, owner in origin.FIELDS_RESERVED.items():
        assert owner.strip(), field


def test_a_degenerate_field_is_written_and_explains_why_it_is_dead():
    for field, reason in origin.FIELDS_DEGENERATE.items():
        assert field in origin.FIELDS_WRITTEN_TODAY, field
        assert len(reason) > 40, field


def test_printed_and_structural_partition_the_union():
    printed, structural = set(origin.FIELDS_PRINTED), set(origin.FIELDS_STRUCTURAL)
    assert printed | structural == set(origin.ORIGIN_UNION)
    assert not (printed & structural)


# ── the vocabulary, classified the same way and checked the same way ──


def test_every_reason_is_classified_exactly_once():
    """#155 froze the FIELDS and left the VOCABULARY unclassified — the same
    class of gap, in the same module, missed by the ship that built the
    mechanism for it. This is the other half."""
    e = set(origin.REASONS_EMITTED_TODAY)
    r, d = set(origin.REASONS_RESERVED), set(origin.REASONS_DEGENERATE)
    assert e | r | d == set(origin.REFUSAL_REASONS)
    assert len(e) + len(r) + len(d) == len(e | r | d), "a reason has two classes"


def test_every_reason_called_emitted_is_actually_recorded(emitted):
    """The teeth, again: run the producers and look."""
    recorded = {
        r[origin.FIELD_REFUSAL_REASON] for r in emitted
        if r[origin.FIELD_REFUSAL_REASON] is not None
    }
    never = sorted(set(origin.REASONS_EMITTED_TODAY) - recorded)
    assert never == [], f"classified emitted but never recorded: {never}"


def test_no_reserved_or_degenerate_reason_is_ever_recorded(emitted):
    recorded = {
        r[origin.FIELD_REFUSAL_REASON] for r in emitted
        if r[origin.FIELD_REFUSAL_REASON] is not None
    }
    leaked = sorted((set(origin.REASONS_RESERVED) | set(origin.REASONS_DEGENERATE)) & recorded)
    assert leaked == [], f"recorded but classified as unavailable: {leaked}"


def test_source_unreachable_is_no_longer_advertised_because_no_record_can_carry_it(emitted):
    """**The pin, inverted — and inverting it is the fix.**

    The previous version of this test asserted the reason WAS advertised and
    called that a gap to be lived with. It is not a gap to live with: the path
    that would use it RAISES, a raising step writes no origin record, and so a
    possible-list naming it told a renderer *"this lookup could have told you
    the store was unreachable"* — a sentence no record could ever be the
    evidence for. ``policy_lookup_v0.POSSIBLE_REFUSAL_REASONS`` no longer names
    it, and this asserts that in the emitted records themselves rather than in
    the constant.

    The reason is **not** deleted. It is still the machine-readable token on
    ``PolicyStoreUnreachableError`` and still reaches a reader — through L-2's
    ``RunStopped`` node, which is where "was this our fault" belongs. It is
    still classified degenerate, because that classification is about what a
    RECORD can carry, and no record can carry this."""
    advertised = {
        reason for r in emitted
        for reason in r[origin.FIELD_POSSIBLE_REFUSAL_REASONS]
    }
    assert advertised, "the premise of this pin is that something IS advertised"
    assert origin.REFUSAL_SOURCE_UNREACHABLE not in advertised, (
        "a producer must not advertise a reason none of its records can carry"
    )
    assert origin.REFUSAL_SOURCE_UNREACHABLE in origin.REASONS_DEGENERATE

    # **Drive the unreachable path itself.** An earlier version of this test
    # asserted the reason was absent from the RECORDED set — and the recorded
    # set came from a fixture whose paths never reach the store failure, so
    # making the reason recordable reddened nothing. An assertion over a set
    # that cannot contain the forbidden thing is not a guard. The pin is that
    # the path RAISES, which is why no record exists to carry the reason.
    class _Unreadable:
        def global_view(self):
            raise RuntimeError("the store is down")

    with pytest.raises(PolicyStoreUnreachableError):
        _lookup_body()(context=_Ctx(_Unreadable()), **{DS_AS_OF: "2024-06-01"})

    with pytest.raises(PolicyStoreUnreachableError):
        _lookup_body()(context=_Ctx(None), **{DS_AS_OF: "2024-06-01"})


def test_a_reserved_reason_names_the_producer_that_will_record_it():
    for reason, owner in origin.REASONS_RESERVED.items():
        assert owner.strip(), reason


# ── and then it goes and looks ────────────────────────────────────────


def test_every_field_called_live_is_actually_emitted(emitted):
    """The teeth. A producer that stops writing a field turns this red."""
    seen = set().union(*(set(r) for r in emitted))
    never = sorted(set(origin.FIELDS_WRITTEN_TODAY) - seen)
    assert never == [], f"classified live but never emitted: {never}"


def test_no_reserved_field_is_emitted_by_anything_shipped(emitted):
    seen = set().union(*(set(r) for r in emitted))
    leaked = sorted(set(origin.FIELDS_RESERVED) & seen)
    assert leaked == [], f"emitted but classified as reserved: {leaked}"


def test_environment_fault_is_never_true_in_any_record_the_system_writes(emitted):
    """**The gap-pin, and it should fail the day the hole closes.** Both
    ENVIRONMENT_FAULT_REASONS are on raising paths, and a raising step writes
    no record — so no record can ever carry True. A renderer must read *"was
    this our fault"* from L-2's RunStopped node instead. Same class as
    ``test_append_only_is_declared_but_not_enforced``."""
    assert all(r[origin.FIELD_ENVIRONMENT_FAULT] is False for r in emitted)
    assert set(origin.ENVIRONMENT_FAULT_REASONS) == {
        origin.REFUSAL_MODEL_UNREACHABLE, origin.REFUSAL_SOURCE_UNREACHABLE
    }


def test_every_refusal_carries_prose_a_reader_can_be_shown(emitted):
    for record in emitted:
        if record[origin.FIELD_REFUSAL_REASON] is not None:
            detail = record[origin.FIELD_REFUSAL_DETAIL]
            assert detail and detail.strip(), record[origin.FIELD_REFUSAL_REASON]


@pytest.mark.parametrize("detail", [None, "", "   "])
def test_a_refusal_without_prose_is_refused_at_build_time(detail):
    """**The failable form**, and it was missing. The test above only inspects
    records the shipped producers emit — and they all supply a detail — so
    deleting the guard reddened nothing. A guard whose removal changes no test
    is not a guard, which is exactly what RULES §9 says.

    The token branches; ``refusal_detail`` is the only thing a reader is ever
    shown. A refusal without it leaves a Record with nothing to say."""
    with pytest.raises(origin.OriginContractError):
        origin.build_origin_record(
            producer_kind=origin.PRODUCER_STRUCTURED_INGEST,
            origin_method=origin.ORIGIN_READ_FROM_SOURCE,
            source_identity_phrase="the probe record",
            source_datastate=DS_RECORD,
            question="What does the probe record state?",
            admitted=False,
            supplied_fields=(),
            possible_refusal_reasons=(origin.REFUSAL_FIELD_ABSENT,),
            refusal_reason=origin.REFUSAL_FIELD_ABSENT,
            refusal_detail=detail,
        )


def test_an_admitted_record_still_needs_no_detail():
    """The rule is conditional on refusing, not a blanket requirement."""
    record = origin.build_origin_record(
        producer_kind=origin.PRODUCER_STRUCTURED_INGEST,
        origin_method=origin.ORIGIN_READ_FROM_SOURCE,
        source_identity_phrase="the probe record",
        source_datastate=DS_RECORD,
        question="What does the probe record state?",
        admitted=True,
        supplied_fields=(origin.FIELD_BASIS,),
        possible_refusal_reasons=(origin.REFUSAL_FIELD_ABSENT,),
        **{origin.FIELD_BASIS: origin.BASIS_STATED},
    )
    assert record[origin.FIELD_REFUSAL_DETAIL] is None


#: The identifier schemes a printed field must never carry (G6). Mirrors
#: the demo renderer's own banned list; the claim is "no IRI on a printed
#: field", and these are what an IRI looks like here.
_IRI_SCHEMES = (
    "datastate:", "capacity:", "runstopped:", "runmanifest:",
    "requestrun:", "pipelinerun:", "prompt:", "policy:",
)


def test_the_one_structural_field_that_leaks_is_the_one_we_classified(emitted):
    """``source_datastate`` holds a DataState IRI and is on records both
    producers write. It is STRUCTURAL — printing it is a G6 leak, and its prose
    counterpart already exists as ``source_identity_phrase``.

    **The check was ``":" in v`` until 2026-08-16, and that proxy is now
    wrong** (coordination §87 T-F12). It stood in for "holds an IRI" and
    was safe only while every printed field held phrasing WE wrote. The
    model reader puts verbatim document text on ``quote`` — a printed
    field — and on ``refusal_detail`` it puts the model's own undecodable
    answer. Both legitimately contain colons; ``DOCUMENT`` above carries
    one inside the quoted span precisely so this case is exercised rather
    than imagined. Widening a guard to reach green is forbidden (RULES
    §12); correcting a proxy that produces false positives by
    construction is not the same act, and the difference is that this one
    still fails on the thing the claim is about — an IRI."""
    assert origin.FIELD_SOURCE_DATASTATE in origin.FIELDS_STRUCTURAL
    assert origin.FIELD_SOURCE_IDENTITY_PHRASE in origin.FIELDS_PRINTED
    quoted = [r for r in emitted if r.get(origin.FIELD_QUOTE)]
    assert quoted, "the premise of the correction is that a quote IS printed"
    assert any(":" in r[origin.FIELD_QUOTE] for r in quoted), (
        "no emitted quote carries a colon, so this test would pass under the "
        "old proxy too and proves nothing — fix the fixture, not the test"
    )
    iri_valued = [
        f for r in emitted for f, v in r.items()
        if isinstance(v, str) and f in origin.FIELDS_PRINTED
        and any(scheme in v for scheme in _IRI_SCHEMES)
    ]
    assert iri_valued == [], f"printed fields holding identifiers: {iri_valued}"
