"""The policy-limit lookup capacity, in isolation.

Two things are being pinned. First, that the lookup produces its value **and**
that value's origin record as declared outputs — a limit read inside a body and
never declared never reaches ``CapacityMMWriter.record``, and the Record is
rendered from the grounding graph and nothing else. Second, that its two
failures behave differently on purpose: a gap in the customer's policy set is a
finding and returns; an unreadable store is our outage and raises.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import family_rule_for
from mindsos_capacity.builtins.origin_v0 import (
    DECISION_SHAPED_CATEGORIES,
    FIELD_ADMITTED,
    FIELD_ENVIRONMENT_FAULT,
    FIELD_POSSIBLE_REFUSAL_REASONS,
    FIELD_PRODUCER_KIND,
    FIELD_QUESTION,
    FIELD_REFUSAL_REASON,
    FIELD_SOURCE_IDENTITY_PHRASE,
    FIELD_SOURCE_IN_FORCE_FROM,
    FIELD_SOURCE_IN_FORCE_TO,
    FIELD_SOURCE_VERSION,
    OriginContractError,
    PRODUCER_POLICY_LOOKUP,
    REFUSAL_NO_SOURCE_IN_FORCE,
    REFUSAL_SOURCE_UNREACHABLE,
    missing_declared_fields,
    opaque_into_decision,
)
from mindsos_capacity.builtins.policy_lookup_v0 import (
    CATEGORY,
    PolicyStoreUnreachableError,
    build_policy_limit_lookup,
)
from mindsos_capacity.family_rules import FamilyDontKnowShape
from mindsos_knowledge.policies import AmbiguousEditionsError

from ._dr_fixtures import (
    CAP_DECISION,
    CAP_LOOKUP,
    DS_AS_OF_DATE,
    DS_FILING_THRESHOLD,
    DS_FILING_THRESHOLD_ORIGIN,
    EDITION_2023,
    POLICY_ID,
    POLICY_PHRASE,
    Context,
    build_kl,
    build_kl_with_both,
    build_capacity_layer,
    lookup_declaration,
)


def _run(kl, as_of):
    body = lookup_declaration().implementation
    return body(context=Context(kl=kl), **{DS_AS_OF_DATE: as_of})


# ── the shape ─────────────────────────────────────────────────────────


def test_the_lookup_declares_the_value_and_its_origin_as_outputs():
    declaration = lookup_declaration()
    assert declaration.outputs == (DS_FILING_THRESHOLD, DS_FILING_THRESHOLD_ORIGIN)
    assert declaration.inputs == (DS_AS_OF_DATE,)


def test_the_authority_is_bound_not_taken_as_an_input():
    """A lookup is *of* an authority. Its IRI, its prose phrase and its output
    DataState are all specific to one, so taking the authority as a runtime
    input would let the identity and the printed prose disagree — with the
    Record printing the prose."""
    assert POLICY_ID not in lookup_declaration().inputs


def test_the_lookup_is_retrieval_and_gets_the_optional_return_contract():
    """Reverses the 2026-08-09 ``capacity:decision:*`` ruling for the LOOKUP.

    That ruling rested on two rules agreeing. ``family_rule_for`` has no caller
    in any shipped module, so what it returned there was a fact about nothing;
    and ``DECISION_SHAPED_CATEGORIES`` guards a capacity that COMPARES a value,
    which is the criterion, not this. Under ``retrieval`` the contract is
    OPTIONAL_RETURN, which is what a lookup that may find nothing needs.
    """
    assert CATEGORY == "retrieval"
    assert family_rule_for(CAP_LOOKUP) is FamilyDontKnowShape.OPTIONAL_RETURN
    assert CATEGORY not in DECISION_SHAPED_CATEGORIES
    assert CAP_DECISION.split(":")[1] in DECISION_SHAPED_CATEGORIES


def test_the_protocol_declares_the_surface_the_body_actually_uses():
    """Makes the ``KLHandle`` declaration load-bearing instead of decorative.

    The body reaches L2 through ``context.kl.global_view()``. Because the
    concrete object is a ``KnowledgeLayer``, that call works whether or not the
    Protocol mentions it — so deleting the declaration breaks nothing and the
    declaration would be a comment. The second assertion is the one that goes
    red on deletion: a handle offering only ``read_at_version`` must NOT satisfy
    ``KLHandle``, because a body handed one cannot select an edition at all.
    """
    from mindsos_capacity import KLHandle

    assert isinstance(build_kl_with_both(), KLHandle)

    class _ReadAtVersionOnly:
        def read_at_version(self, iri, version): ...

    assert not isinstance(_ReadAtVersionOnly(), KLHandle), (
        "KLHandle no longer declares the read surface its only caller uses; "
        "the policy lookup would reach past the protocol into the concrete "
        "KnowledgeLayer and nothing would record the dependency."
    )


def test_a_source_phrase_that_is_an_identifier_is_refused_at_build_time():
    """A Decision Record forbids every IRI and every MindsOS term. Catching it
    here beats catching it in front of a lawyer."""
    with pytest.raises(OriginContractError):
        build_policy_limit_lookup(
            name="bad_phrase",
            policy_id=POLICY_ID,
            source_identity_phrase="policy:filing_threshold",
            question="What was in force on {as_of}?",
            limit_datastate_iri=DS_FILING_THRESHOLD,
            as_of_datastate_iri=DS_AS_OF_DATE,
        )


# ── the admitted path ─────────────────────────────────────────────────


def test_the_limit_and_its_origin_come_back_together():
    outputs = _run(build_kl_with_both(), "2024-04-15")
    assert outputs[DS_FILING_THRESHOLD] == 29200
    record = outputs[DS_FILING_THRESHOLD_ORIGIN]
    assert record[FIELD_PRODUCER_KIND] == PRODUCER_POLICY_LOOKUP
    assert record[FIELD_ADMITTED] is True
    assert record[FIELD_SOURCE_VERSION] == "2024.1"
    assert record[FIELD_SOURCE_IN_FORCE_FROM] == "2024-01-01"
    assert record[FIELD_SOURCE_IDENTITY_PHRASE] == POLICY_PHRASE
    assert record[FIELD_ENVIRONMENT_FAULT] is False
    assert missing_declared_fields(record) == []


def test_the_version_lives_in_the_origin_record_not_as_a_second_input():
    """The money sentence is *"from the filing-threshold policy, version 2024.1,
    in force since 2024-01-01"* — one statement about where the limit came from.
    The criterion does not compute with the version, so wiring it in as a third
    consumed input would put provenance in the position of an operand. It is
    still graph-resident: the origin record is itself a declared output."""
    record = _run(build_kl_with_both(), "2024-04-15")[DS_FILING_THRESHOLD_ORIGIN]
    assert (record[FIELD_SOURCE_VERSION], record[FIELD_SOURCE_IN_FORCE_FROM]) == (
        "2024.1",
        "2024-01-01",
    )


def test_a_closed_window_reports_its_end_and_an_open_one_does_not():
    """``in_force_to`` is producer-declared but NOT in ``supplied_fields`` — an
    open-ended edition has none, and promising a field a producer cannot always
    populate would make every current edition look defective."""
    closed = _run(build_kl_with_both(), "2023-06-30")[DS_FILING_THRESHOLD_ORIGIN]
    assert closed[FIELD_SOURCE_IN_FORCE_TO] == "2023-12-31"
    open_ended = _run(build_kl_with_both(), "2024-04-15")[DS_FILING_THRESHOLD_ORIGIN]
    assert FIELD_SOURCE_IN_FORCE_TO not in open_ended
    assert missing_declared_fields(open_ended) == []


def test_the_question_names_the_date_that_was_asked_about():
    record = _run(build_kl_with_both(), "2024-04-15")[DS_FILING_THRESHOLD_ORIGIN]
    assert "2024-04-15" in record[FIELD_QUESTION]
    assert "datastate:" not in record[FIELD_QUESTION]


def test_two_dates_over_one_store_give_two_limits_and_two_versions():
    """Run 5, and the trap it carries: the as-of date is an INPUT, never
    something read out of the document. Otherwise this silently becomes
    "different documents give different limits", which is the opposite of the
    point."""
    kl = build_kl_with_both()
    old = _run(kl, "2023-06-30")
    new = _run(kl, "2024-04-15")
    assert old[DS_FILING_THRESHOLD] == 27700
    assert new[DS_FILING_THRESHOLD] == 29200
    assert old[DS_FILING_THRESHOLD_ORIGIN][FIELD_SOURCE_VERSION] == "2023.1"
    assert new[DS_FILING_THRESHOLD_ORIGIN][FIELD_SOURCE_VERSION] == "2024.1"


# ── the two refusals, which are not the same kind of thing ────────────


def test_no_edition_in_force_returns_a_finding_and_does_not_raise():
    """A gap in the customer's own policy set. It returns, so the criterion sees
    a ``None`` and the whole run stays renderable — a refusal that killed the
    step would replace a wrong answer with no Record at all."""
    outputs = _run(build_kl(EDITION_2023), "2019-04-15")
    assert outputs[DS_FILING_THRESHOLD] is None
    record = outputs[DS_FILING_THRESHOLD_ORIGIN]
    assert record[FIELD_ADMITTED] is False
    assert record[FIELD_REFUSAL_REASON] == REFUSAL_NO_SOURCE_IN_FORCE
    assert record[FIELD_ENVIRONMENT_FAULT] is False
    assert missing_declared_fields(record) == []


def test_a_refusal_still_declares_both_reasons_it_could_ever_give():
    """Lets a renderer tell "a lookup would never say quote_not_found_in_source"
    from "this lookup happened not to"."""
    record = _run(build_kl(EDITION_2023), "2019-04-15")[DS_FILING_THRESHOLD_ORIGIN]
    assert set(record[FIELD_POSSIBLE_REFUSAL_REASONS]) == {
        REFUSAL_NO_SOURCE_IN_FORCE,
        REFUSAL_SOURCE_UNREACHABLE,
    }


def test_an_unreadable_store_raises_and_never_becomes_a_finding():
    """Our outage. Reported as a stopped run by L-2, never as a gap in the
    customer's policy set — that Record would be false."""
    with pytest.raises(PolicyStoreUnreachableError) as excinfo:
        _run(None, "2024-04-15")
    assert REFUSAL_SOURCE_UNREACHABLE in str(excinfo.value)


def test_overlapping_editions_propagate_rather_than_being_called_a_gap():
    """``no_source_in_force`` means *there is no edition*. Saying it here would
    be false: there are two, and the store contradicts itself."""
    kl = build_kl(
        EDITION_2023,
        dict(
            version="2023.2",
            in_force_from="2023-06-01",
            in_force_to="2023-12-31",
            stated_value=28000,
            text="An overlapping restatement.",
        ),
    )
    with pytest.raises(AmbiguousEditionsError):
        _run(kl, "2023-07-01")


# ── D15, non-vacuously ────────────────────────────────────────────────


def test_no_opaque_value_reaches_the_criterion():
    cl, session = build_capacity_layer()
    assert opaque_into_decision(cl, user_id=session.user_id) == []


def test_the_d15_walk_would_catch_an_opaque_operand():
    """Shown red. A guard that has never found anything is a guard nobody has
    tested — the origin records ARE opaque, so wiring one into the criterion is
    a real violation and the walk must name it."""
    from mindsos_capacity import Capacity

    cl, session = build_capacity_layer()
    cl.register_capacity(
        Capacity(
            name="dr_offender",
            category="decision",
            inputs=(DS_FILING_THRESHOLD_ORIGIN,),
            outputs=(),
            implementation=lambda **kw: {},
        ),
        session=session,
    )
    offenders = opaque_into_decision(cl, user_id=session.user_id)
    assert (DS_FILING_THRESHOLD_ORIGIN, "capacity:decision:dr_offender") in offenders
