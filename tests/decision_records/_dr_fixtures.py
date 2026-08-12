"""Shared setup for the Decision Records lookup + criterion tests.

**This module holds content, not mechanism.** The as-of selection lives in
``mindsos_knowledge.policies`` and the lookup capacity in
``mindsos_capacity.builtins.policy_lookup_v0``, both core (RULES §8). What is
here is one authority, one criterion and one prose vocabulary — a particular
question somebody is asking, which core does not own and must not ship. When the
Decision Records demo gains a home of its own, this moves there unchanged.

The reader is a **stand-in**. Item 5 of ``DECISION_RECORDS_V0_PLAN.md`` builds
the real structured-ingest reader with a declared shape and a ``field_absent``
refusal; until then this returns a fixed value so the route has two producers to
compose. It is marked so nobody mistakes it for the shipped one.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from mindsos_capacity import (
    Capacity,
    CapacityLayer,
    DataState,
    INPUT_GROUP_ALL_REQUIRED,
    ShapeDescriptor,
)
from mindsos_capacity.builtins.origin_v0 import (
    BASIS_STATED,
    FIELD_BASIS,
    ORIGIN_READ_BY_MODEL,
    PRODUCER_DOCUMENT_READING,
    REFUSAL_FIELD_ABSENT,
    build_origin_record,
    origin_record_iri,
)
from mindsos_capacity.builtins.policy_lookup_v0 import (
    build_policy_limit_lookup,
    policy_limit_datastates,
    policy_lookup_iri,
)
from mindsos_knowledge.identifiers import ROLE_POLICIES
from mindsos_knowledge.knowledge_layer import KnowledgeLayer
from mindsos_knowledge.policies import write_policy_edition

# ── The authority ──────────────────────────────────────────────────────

POLICY_ID = "policy:filing_threshold"
POLICY_PHRASE = "the filing-threshold policy"
POLICY_QUESTION = "What filing threshold was in force on {as_of}?"

EDITION_2023 = dict(
    version="2023.1",
    in_force_from="2023-01-01",
    in_force_to="2023-12-31",
    stated_value=27700,
    text="A return must be filed where gross income reaches 27,700.",
)
EDITION_2024 = dict(
    version="2024.1",
    in_force_from="2024-01-01",
    in_force_to=None,
    stated_value=29200,
    text="A return must be filed where gross income reaches 29,200.",
)

# ── DataState vocabulary ───────────────────────────────────────────────
#
# One value, one DataState type. The blackboard holds one value per IRI and
# ``CapacityMMWriter.index`` overwrites, so a type reused for two values loses
# one of them and the grounding graph wires the wrong producer.

DS_DOCUMENT = "datastate:dr.document"
DS_AS_OF_DATE = "datastate:dr.as_of_date"
DS_GROSS_INCOME = "datastate:dr.gross_income"
DS_GROSS_INCOME_ORIGIN = origin_record_iri(DS_GROSS_INCOME)
DS_FILING_THRESHOLD = "datastate:dr.filing_threshold"
DS_FILING_THRESHOLD_ORIGIN = origin_record_iri(DS_FILING_THRESHOLD)
DS_FILING_VERDICT = "datastate:dr.filing_verdict"

STARTS = (DS_DOCUMENT, DS_AS_OF_DATE)

LOOKUP_NAME = "dr_lookup_filing_threshold"
CAP_LOOKUP = policy_lookup_iri(LOOKUP_NAME)
CAP_READER = "capacity:comprehension:dr_read_gross_income"
CAP_DECISION = "capacity:decision:dr_filing_requirement"

# ── The criterion's outcomes ───────────────────────────────────────────
#
# Prose, because the Record prints them, and a closed set, because code
# branches on them. Not a verdict dataclass: the four canonical ones in
# ``CapacityContext`` are L4-orchestration shapes carrying a ``rationale``
# string, and the Record's "why" comes from the grounding graph — never from
# prose a capacity wrote about itself.

VERDICT_MUST_FILE = "a return must be filed"
VERDICT_NO_FILING = "no return is required"
VERDICT_NOT_DETERMINED = "not determined"

USER = "dr_lane_user"


class Session:
    """Minimal SessionProtocol stand-in (mirrors tests/phase_30/_fixtures)."""

    def __init__(self, user_id: str = USER) -> None:
        self.user_id = user_id
        self.session_id = f"sess:{user_id}"

    def has(self, capability: str) -> bool:
        return True


class Context:
    """The two fields a lookup body reads. Not a CapacityContext — a body that
    only ever touches ``kl`` should be testable without one, and building a
    real one here would hide which fields the body actually depends on."""

    def __init__(self, kl: Any = None, user_id: str = USER) -> None:
        self.kl = kl
        self.user_id = user_id
        self.session_id = f"sess:{user_id}"


# ── The store ──────────────────────────────────────────────────────────


def build_kl(*editions: Dict[str, Any]) -> KnowledgeLayer:
    """A KnowledgeLayer whose **Global** policies role holds ``editions``.

    Global because an authority is shared: a per-user copy of a stated
    threshold is the shape that lets one user's override silently restate what
    the policy said, which is the objection that kept this store out of
    ``learned-parameters``.
    """
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, ROLE_POLICIES, "global")
    for edition in editions:
        write_policy_edition(handle, policy_id=POLICY_ID, **edition)
    return kl


def build_kl_with_both() -> KnowledgeLayer:
    return build_kl(EDITION_2023, EDITION_2024)


# ── The capacities ─────────────────────────────────────────────────────


def _reader_body(context: Any = None, **inputs: Any) -> Dict[str, Any]:
    """STAND-IN for item 5's structured-ingest reader. Not the shipped one."""
    document = inputs.get(DS_DOCUMENT)
    if document is None or "gross income" not in str(document):
        return {
            DS_GROSS_INCOME: None,
            DS_GROSS_INCOME_ORIGIN: build_origin_record(
                producer_kind=PRODUCER_DOCUMENT_READING,
                origin_method=ORIGIN_READ_BY_MODEL,
                source_identity_phrase="their filed return",
                source_datastate=DS_DOCUMENT,
                question="What gross income does the return state?",
                admitted=False,
                supplied_fields=(),
                possible_refusal_reasons=(REFUSAL_FIELD_ABSENT,),
                refusal_reason=REFUSAL_FIELD_ABSENT,
                refusal_detail="their filed return does not state a gross income.",
            ),
        }
    return {
        DS_GROSS_INCOME: 61000,
        DS_GROSS_INCOME_ORIGIN: build_origin_record(
            producer_kind=PRODUCER_DOCUMENT_READING,
            origin_method=ORIGIN_READ_BY_MODEL,
            source_identity_phrase="their filed return",
            source_datastate=DS_DOCUMENT,
            question="What gross income does the return state?",
            admitted=True,
            supplied_fields=(FIELD_BASIS,),
            possible_refusal_reasons=(REFUSAL_FIELD_ABSENT,),
            **{FIELD_BASIS: BASIS_STATED},
        ),
    }


def _decision_body(context: Any = None, **inputs: Any) -> Dict[str, Any]:
    """Typed to this criterion, deliberately not a reusable comparator.

    The ``None`` check is the load-bearing line. ``core-dispatch-value-
    validation`` is deferred, so ``_validate_inputs`` checks presence and never
    the value: a refused lookup arrives here as a present key holding ``None``
    and nothing in core will stop it. A body that skipped this check would
    compare an income against ``None`` and either crash or state an outcome it
    did not derive. Which value was missing, and why, is already on the
    grounding graph in that value's origin record — this only has to refuse to
    guess.
    """
    income = inputs.get(DS_GROSS_INCOME)
    threshold = inputs.get(DS_FILING_THRESHOLD)
    if income is None or threshold is None:
        return {DS_FILING_VERDICT: VERDICT_NOT_DETERMINED}
    verdict = VERDICT_MUST_FILE if income >= threshold else VERDICT_NO_FILING
    return {DS_FILING_VERDICT: verdict}


def _datastates() -> list:
    limit, limit_origin = policy_limit_datastates(
        limit_name="dr.filing_threshold",
        limit_elem="int",
        limit_description="the gross income at which a return must be filed",
    )
    return [
        DataState(
            name="dr.document",
            shape=ShapeDescriptor.scalar("str"),
            description="the return as filed",
        ),
        DataState(
            name="dr.as_of_date",
            shape=ShapeDescriptor.scalar("str"),
            description="the date the question is asked about",
        ),
        DataState(
            name="dr.gross_income",
            shape=ShapeDescriptor.scalar("int"),
            description="the gross income the return states",
        ),
        DataState(
            name="dr.gross_income_origin",
            shape=ShapeDescriptor.opaque("origin.record.v0"),
            description="where the gross income came from",
        ),
        limit,
        limit_origin,
        DataState(
            name="dr.filing_verdict",
            shape=ShapeDescriptor.scalar("str"),
            description="whether a return must be filed",
        ),
    ]


def lookup_declaration() -> Capacity:
    return build_policy_limit_lookup(
        name=LOOKUP_NAME,
        policy_id=POLICY_ID,
        source_identity_phrase=POLICY_PHRASE,
        question=POLICY_QUESTION,
        limit_datastate_iri=DS_FILING_THRESHOLD,
        as_of_datastate_iri=DS_AS_OF_DATE,
    )


def decision_declaration() -> Capacity:
    return Capacity(
        name="dr_filing_requirement",
        category="decision",
        inputs=(DS_GROSS_INCOME, DS_FILING_THRESHOLD),
        outputs=(DS_FILING_VERDICT,),
        input_group=INPUT_GROUP_ALL_REQUIRED,
        description="whether the stated income reaches the threshold in force",
        printable_phrase="the filing-requirement test",
        implementation=_decision_body,
    )


def reader_declaration() -> Capacity:
    return Capacity(
        name="dr_read_gross_income",
        category="comprehension",
        inputs=(DS_DOCUMENT,),
        outputs=(DS_GROSS_INCOME, DS_GROSS_INCOME_ORIGIN),
        input_group=INPUT_GROUP_ALL_REQUIRED,
        description="reads the gross income the return states",
        printable_phrase="reading the return as filed",
        implementation=_reader_body,
    )


def build_capacity_layer(session: Optional[Session] = None) -> "tuple":
    """Register the three capacities **Local**, and return ``(cl, session)``.

    Local because ``register_capacity`` validates inputs and outputs against the
    target realm's DataState graph and ``_mirror_global_datastates`` copies
    Global→Local only — a Global capacity cannot declare a Local DataState, so
    the mixed-realm arrangement is unbuildable today (``core-datastate-realm-
    free``). The **store** is Global regardless: that is L2 and the constraint
    does not reach it.
    """
    session = session or Session()
    cl = CapacityLayer()
    for datastate in _datastates():
        cl.register_datastate(datastate, session=session, allow_new_realm=True)
    for declaration in (
        reader_declaration(),
        lookup_declaration(),
        decision_declaration(),
    ):
        cl.register_capacity(declaration, session=session)
    return cl, session


INITIAL_2024 = {
    DS_DOCUMENT: "gross income of 61,000 for tax year 2024",
    DS_AS_OF_DATE: "2024-04-15",
}
INITIAL_2023 = {
    DS_DOCUMENT: "gross income of 61,000 for tax year 2023",
    DS_AS_OF_DATE: "2023-04-15",
}
INITIAL_UNCOVERED = {
    DS_DOCUMENT: "gross income of 61,000 for tax year 2019",
    DS_AS_OF_DATE: "2019-04-15",
}
