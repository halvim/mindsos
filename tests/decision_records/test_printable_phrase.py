"""A capacity carries the phrase a Record uses to name it.

**Why the field exists.** A run's grounding graph carries a capacity by IRI
and nothing else — ``CapacityInstance.value`` is the IRI and its only
property is ``capacity``. The criterion writes no origin record (ADR-0208
D3), so when a Record has to say *who decided this* or *where did this stop*
there is no prose anywhere in the graph. Probe D found exactly three such
gaps; this closes one of them.

**Why not ``description``.** The criterion's description is
*"whether the stated income reaches the threshold in force"* — a question,
written for a developer, which renders as *"decided by whether the stated
income reaches the threshold in force"*. One field cannot answer both
*what does this do* and *what is this called*.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import Capacity, CapacityLayer, DataState, ShapeDescriptor
from mindsos_capacity.exceptions import CapacityRegistrationError
from mindsos_capacity.printable import (
    PhraseNotPrintable,
    assert_printable_phrase,
    printable_phrase_problem,
)

from ._dr_fixtures import (
    CAP_DECISION,
    CAP_LOOKUP,
    CAP_READER,
    Session,
    build_capacity_layer,
    decision_declaration,
    lookup_declaration,
    reader_declaration,
)

RECORD_FORBIDDEN = (
    "capacity", "pipeline", "datastate", "metagraph",
    "layer", "verdict", "iri", "blackboard",
)


def _register(cl, session, declaration):
    cl.register_datastate(
        DataState(name="dr.pp_in", shape=ShapeDescriptor.scalar("str"), description="a thing"),
        session=session, allow_new_realm=True, if_exists="ignore",
    )
    cl.register_datastate(
        DataState(name="dr.pp_out", shape=ShapeDescriptor.scalar("str"), description="another thing"),
        session=session, allow_new_realm=True, if_exists="ignore",
    )
    return cl.register_capacity(declaration, session=session)


def _cap(**kw):
    return Capacity(
        name=kw.pop("name", "pp_probe"),
        category="decision",
        inputs=("datastate:dr.pp_in",),
        outputs=("datastate:dr.pp_out",),
        implementation=lambda context=None, **i: {"datastate:dr.pp_out": "x"},
        **kw,
    )


# ── the field ─────────────────────────────────────────────────────────


def test_every_decision_records_capacity_declares_one():
    """All three, because a Record may have to name any of them — the
    criterion on the 'therefore' line, either producer on a stopped run."""
    for declaration in (reader_declaration(), lookup_declaration(), decision_declaration()):
        assert declaration.printable_phrase, declaration.iri
        assert printable_phrase_problem(declaration.printable_phrase, "p") is None


def test_the_phrase_is_not_the_description():
    """Red if anyone 'simplifies' this by reusing description."""
    criterion = decision_declaration()
    assert criterion.printable_phrase != criterion.description
    assert criterion.printable_phrase == "the filing-requirement test"


def test_the_lookup_derives_a_phrase_from_the_authority_it_consults():
    assert lookup_declaration().printable_phrase == "consulting the filing-threshold policy"


def test_no_declared_phrase_leaks_record_vocabulary():
    for declaration in (reader_declaration(), lookup_declaration(), decision_declaration()):
        lowered = declaration.printable_phrase.lower()
        assert [w for w in RECORD_FORBIDDEN if w in lowered] == [], declaration.iri


# ── it reaches the registered node ────────────────────────────────────


def test_the_phrase_is_persisted_on_the_registered_node():
    """A property, not only an in-memory field: whoever mints the run
    manifest may read either, and both must agree."""
    cl, session = build_capacity_layer()
    mg = cl._metagraph_for(session.user_id)
    # One graph per category (capacity:comprehension, capacity:retrieval,
    # capacity:decision), not one capacity graph — so look across all of them.
    registered = {
        nid: (n.properties or {}).get("printable_phrase")
        for g in mg.graphs.values() for nid, n in g.nodes.items()
    }
    for iri, expected in (
        (CAP_READER, "reading the return as filed"),
        (CAP_LOOKUP, "consulting the filing-threshold policy"),
        (CAP_DECISION, "the filing-requirement test"),
    ):
        assert registered[iri] == expected


def test_a_capacity_without_a_phrase_writes_no_property():
    """Optional by construction — every capacity registered before this
    field existed is byte-identical on the node."""
    cl, session = CapacityLayer(), Session("pp_user_absent")
    node = _register(cl, session, _cap())
    assert (node.properties or {}).get("description", None) is None
    assert "printable_phrase" not in (node.properties or {})


# ── the guard ─────────────────────────────────────────────────────────


def test_registration_refuses_a_phrase_carrying_an_identifier():
    """Shown red by mutation: delete the printable_phrase block in
    ``_validate_contract_fields`` and this is the test that goes red."""
    cl, session = CapacityLayer(), Session("pp_user_iri")
    with pytest.raises(CapacityRegistrationError) as excinfo:
        _register(cl, session, _cap(printable_phrase="capacity:decision:dr_filing_requirement"))
    assert "printable_phrase" in str(excinfo.value)


def test_registration_refuses_a_phrase_carrying_a_bare_colon():
    cl, session = CapacityLayer(), Session("pp_user_colon")
    with pytest.raises(CapacityRegistrationError):
        _register(cl, session, _cap(printable_phrase="the test: version 2"))


def test_registration_refuses_a_whitespace_phrase_but_allows_an_absent_one():
    """Absent means 'this capacity has no Record-facing name yet'. Present
    and blank means someone declared one and got it wrong."""
    cl, session = CapacityLayer(), Session("pp_user_blank")
    with pytest.raises(CapacityRegistrationError):
        _register(cl, session, _cap(printable_phrase="   "))


# ── one rule, two exception types ─────────────────────────────────────


def test_the_same_rule_backs_both_callers():
    """``origin_v0.assert_printable_phrase`` and ``register_capacity`` must
    never diverge — that is why the rule is a shared pure function."""
    from mindsos_capacity.builtins.origin_v0 import (
        OriginContractError,
        assert_printable_phrase as origin_assert,
    )

    bad = "datastate:dr.gross_income"
    assert printable_phrase_problem(bad, "p") is not None
    with pytest.raises(OriginContractError):
        origin_assert(bad, "source_identity_phrase")
    with pytest.raises(PhraseNotPrintable):
        assert_printable_phrase(bad, "p")


def test_the_shared_rule_cannot_catch_a_leaked_datastate_name():
    """Stated as a behaviour so nobody assumes this guard is the ceiling. A
    DataState name carries no colon, so refusing it needs the name in hand —
    ``policy_lookup_v0.assert_printable_description`` does that."""
    assert printable_phrase_problem("where dr.filing_threshold came from", "p") is None
