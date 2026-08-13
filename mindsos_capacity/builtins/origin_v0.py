"""Origin records v0 — where a value came from, for any producer.

**Not a comprehension concept.** A Decision Record must say where *every*
value came from, and the most load-bearing origin statement in the product
— *"from the claims policy, version 4, in force since 12 March"* — is
produced by a ``decision``-family lookup that never touches a language
model. If this shape lived in the comprehension family, the one origin
statement the product turns on would be the one that could not use it.
That is why it is here and not there.

**Placement.** ``mindsos_capacity/builtins/`` is the established home for
opt-in families core does **not** bootstrap (``reduction_v0`` sets the
precedent: not in ``FUNCTIONAL_CATEGORIES``, graph created lazily at first
register). Nothing here is bootstrapped and nothing enters a Global catalog
unless a caller registers it. Promotion to core proper is a later,
deliberate move — see the origin-record ADR draft.

**The union is v0 and NOT frozen.** Neither consumer exists yet: no Record
renderer, no policy lookup. A field set frozen before its consumers are
built is a guess with a process attached. :data:`ORIGIN_UNION` is the
current membership; it is closed **by agreement**, and a new producer kind
is a negotiation rather than a pull request. Freeze after the second
producer proves it.

**Two rules the renderer depends on.**

1. *Never infer from absence.* A missing ``quote`` on a lookup record is
   normal; a missing ``quote`` on a document reading means something went
   wrong. Absence cannot mean the same thing across producers, so every
   record declares :data:`FIELD_PRODUCER_KIND` and
   :data:`FIELD_SUPPLIED_FIELDS` — what this producer *always* populates.
   Inside that list a missing value is a defect; outside it, normal.
2. *Tokens branch, phrases print.* A Decision Record is read by claims
   managers and lawyers and forbids every IRI and every MindsOS term, but
   code still needs something stable to switch on and must never switch by
   parsing English. Every token has a paired registered phrase. This is the
   shipped ``FindVerdict.reason`` / ``.detail`` split.

**Denormalised on purpose.** ``origin_producer_kind`` and
``supplied_fields`` are written onto every record rather than looked up
from this module at render time. An Episode archived today and rendered in
a year must not depend on a module that has since gained a producer — a
Record states what was true when the decision ran.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from ..identifiers import parse_capacity_iri
from ..printable import printable_phrase_problem

# ── Producer kinds ─────────────────────────────────────────────────────

#: A language model read a document. (``comprehension_v0``.)
PRODUCER_DOCUMENT_READING = "document_reading"
#: A value arrived already typed, from a structured export or feed.
PRODUCER_STRUCTURED_INGEST = "structured_ingest"
#: A stored, versioned authority was consulted — a policy, a rate card.
PRODUCER_POLICY_LOOKUP = "policy_lookup"

PRODUCER_KINDS: Tuple[str, ...] = (
    PRODUCER_DOCUMENT_READING,
    PRODUCER_STRUCTURED_INGEST,
    PRODUCER_POLICY_LOOKUP,
)

# ── How a value entered MindsOS ────────────────────────────────────────

#: Taken from an authoritative source as it stood there.
ORIGIN_READ_FROM_SOURCE = "read_from_source"
#: Put into the world by a party — a customer, a supplier, a claimant.
ORIGIN_ASSERTED_BY_PARTY = "asserted_by_party"
#: A language model read it out of prose. Named ``read_by_model`` and not
#: ``inferred_by_model``: it sits beside ``basis`` in the same record and
#: the old name read as a contradiction with ``basis: stated``.
ORIGIN_READ_BY_MODEL = "read_by_model"

ORIGIN_METHODS: Tuple[str, ...] = (
    ORIGIN_READ_FROM_SOURCE,
    ORIGIN_ASSERTED_BY_PARTY,
    ORIGIN_READ_BY_MODEL,
)

#: Phrase per method. Registered prose, because the Record prints it.
ORIGIN_METHOD_PHRASES: Mapping[str, str] = {
    ORIGIN_READ_FROM_SOURCE: "read from the source",
    ORIGIN_ASSERTED_BY_PARTY: "asserted by a party",
    ORIGIN_READ_BY_MODEL: "read by a language model",
}

# ── Where the value sat in the source ──────────────────────────────────

#: Present in the source as written.
BASIS_STATED = "stated"
#: Derived from what surrounds it rather than written out.
BASIS_INFERRED = "inferred"
BASES: Tuple[str, ...] = (BASIS_STATED, BASIS_INFERRED)

# ── Refusal reasons — closed, because consumers branch on them ─────────

REFUSAL_MODEL_DECLINED = "model_declined"
REFUSAL_FIELD_ABSENT = "field_absent"
REFUSAL_QUOTE_NOT_IN_SOURCE = "quote_not_found_in_source"
REFUSAL_MALFORMED_RESPONSE = "malformed_response"
#: The reading service could not be reached. An **environment fault**.
REFUSAL_MODEL_UNREACHABLE = "model_unreachable"
#: A value came back that will not fit its declared shape ("about seven
#: weeks" for a day count). A reading failure, recorded beside the words
#: that caused it.
REFUSAL_VALUE_NOT_COERCIBLE = "value_not_coercible"
#: A versioned source was consulted and holds no edition covering the
#: requested date. A **finding about the customer's case** — a gap in their
#: own policy set that nobody reviewed — so ``environment_fault`` stays False
#: and it belongs in the refusal list.
REFUSAL_NO_SOURCE_IN_FORCE = "no_source_in_force"
#: The store itself could not be reached. The exact analogue of
#: ``model_unreachable``, and an environment fault for the same reason.
REFUSAL_SOURCE_UNREACHABLE = "source_unreachable"

REFUSAL_REASONS: Tuple[str, ...] = (
    REFUSAL_MODEL_DECLINED,
    REFUSAL_FIELD_ABSENT,
    REFUSAL_QUOTE_NOT_IN_SOURCE,
    REFUSAL_MALFORMED_RESPONSE,
    REFUSAL_MODEL_UNREACHABLE,
    REFUSAL_VALUE_NOT_COERCIBLE,
    REFUSAL_NO_SOURCE_IN_FORCE,
    REFUSAL_SOURCE_UNREACHABLE,
)

#: Reasons that are a fault in **our** environment, not a fact about the
#: customer's case. They must never pad a customer's refusal list: *"the
#: document does not say"* is a finding; *"our reading service was down"*
#: is an outage.
ENVIRONMENT_FAULT_REASONS: Tuple[str, ...] = (
    REFUSAL_MODEL_UNREACHABLE,
    REFUSAL_SOURCE_UNREACHABLE,
)

# ── The union ──────────────────────────────────────────────────────────

# The spine — supplied by EVERY producer, whatever it is.
FIELD_PRODUCER_KIND = "origin_producer_kind"
FIELD_SUPPLIED_FIELDS = "supplied_fields"
FIELD_ORIGIN_METHOD = "origin_method"
FIELD_ORIGIN_METHOD_PHRASE = "origin_method_phrase"
FIELD_SOURCE_IDENTITY_PHRASE = "source_identity_phrase"
FIELD_SOURCE_DATASTATE = "source_datastate"
FIELD_QUESTION = "question"
FIELD_ADMITTED = "admitted"
FIELD_REFUSAL_REASON = "refusal_reason"
FIELD_REFUSAL_DETAIL = "refusal_detail"
FIELD_ENVIRONMENT_FAULT = "environment_fault"
#: Which of :data:`REFUSAL_REASONS` this producer could ever emit. The reason
#: vocabulary is a **global closed union** — the renderer must branch on one
#: vocabulary, not one that depends on who wrote the record — so this is the
#: ``supplied_fields`` move applied to reasons: it lets a renderer tell "a
#: lookup would never say ``quote_not_found_in_source``" from "this lookup
#: happened not to".
FIELD_POSSIBLE_REFUSAL_REASONS = "possible_refusal_reasons"

SPINE: Tuple[str, ...] = (
    FIELD_PRODUCER_KIND,
    FIELD_SUPPLIED_FIELDS,
    FIELD_ORIGIN_METHOD,
    FIELD_ORIGIN_METHOD_PHRASE,
    FIELD_SOURCE_IDENTITY_PHRASE,
    FIELD_SOURCE_DATASTATE,
    FIELD_QUESTION,
    FIELD_ADMITTED,
    FIELD_REFUSAL_REASON,
    FIELD_REFUSAL_DETAIL,
    FIELD_ENVIRONMENT_FAULT,
    FIELD_POSSIBLE_REFUSAL_REASONS,
)

# Producer-declared — supplied by some producers and not others, which is
# exactly why SUPPLIED_FIELDS exists.
FIELD_ORIGIN_PARTY = "origin_party"
FIELD_ORIGIN_PARTY_PHRASE = "origin_party_phrase"
FIELD_BASIS = "basis"
FIELD_EXPECTED_BASIS = "expected_basis"
FIELD_QUOTE = "quote"
FIELD_CLAIMED_QUOTE = "claimed_quote"
FIELD_QUOTE_VERIFIED = "quote_verified"
FIELD_QUOTE_OFFSETS = "quote_offsets"
FIELD_SOURCE_VERSION = "source_version"
FIELD_SOURCE_IN_FORCE_FROM = "source_in_force_from"
FIELD_SOURCE_IN_FORCE_TO = "source_in_force_to"
FIELD_MODEL_ID = "model_id"
FIELD_MODEL_VERSION = "model_version"
FIELD_PROMPT_IRI = "prompt_iri"
FIELD_PROMPT_VERSION = "prompt_version"
FIELD_TEMPERATURE = "temperature"
FIELD_REQUEST_KEY = "request_key"
FIELD_RECORDED = "recorded"

PRODUCER_DECLARED: Tuple[str, ...] = (
    FIELD_ORIGIN_PARTY,
    FIELD_ORIGIN_PARTY_PHRASE,
    FIELD_BASIS,
    FIELD_EXPECTED_BASIS,
    FIELD_QUOTE,
    FIELD_CLAIMED_QUOTE,
    FIELD_QUOTE_VERIFIED,
    FIELD_QUOTE_OFFSETS,
    FIELD_SOURCE_VERSION,
    FIELD_SOURCE_IN_FORCE_FROM,
    FIELD_SOURCE_IN_FORCE_TO,
    FIELD_MODEL_ID,
    FIELD_MODEL_VERSION,
    FIELD_PROMPT_IRI,
    FIELD_PROMPT_VERSION,
    FIELD_TEMPERATURE,
    FIELD_REQUEST_KEY,
    FIELD_RECORDED,
)

#: Everything a producer may write. v0 — closed by agreement, not frozen.
ORIGIN_UNION: Tuple[str, ...] = SPINE + PRODUCER_DECLARED


# ── The freeze (ADR-0207 amendment 2) ──────────────────────────────────
#
# This module has said from the start that the union is *"closed by agreement…
# freeze after the second producer proves it."* Three producers have shipped —
# document reading, the policy lookup, structured ingest — and nobody froze it.
# A §12 check on 2026-08-12 found what that cost: **the system writes 16 of
# these 30 fields**, and one of them can never carry information at all. None
# of that was visible anywhere, because a union with no classification cannot
# tell "nobody has built that producer yet" from "that field is dead".
#
# The freeze is a CLASSIFICATION, not a deletion. Nothing is removed: the model
# fields are real and the seam will write them. What changes is that every
# field now has to say which of three things it is, and a test enforces it.

# ── The vocabulary freeze (the second §12 check) ───────────────────────
#
# PR #155 froze this union's FIELDS and left its VOCABULARIES unclassified —
# the same class of gap, in the same module, missed by the ship that built the
# mechanism for it. ``REFUSAL_REASONS`` declares eight tokens; the shipped
# system can put **three** of them in a record.
#
# Verified by grep across every call site, not inferred from the two producers
# in this package: only ``structured_ingest_v0`` and ``policy_lookup_v0`` ever
# pass a ``refusal_reason`` in production.

#: A shipped producer can put these in a record.
REASONS_EMITTED_TODAY: Tuple[str, ...] = (
    REFUSAL_FIELD_ABSENT,
    REFUSAL_VALUE_NOT_COERCIBLE,
    REFUSAL_NO_SOURCE_IN_FORCE,
)

#: Declared for a producer that does not exist, each naming it.
REASONS_RESERVED: Mapping[str, str] = {
    REFUSAL_MODEL_DECLINED: "the model reader (comprehension_v0, LLM seam)",
    REFUSAL_MALFORMED_RESPONSE: "the model reader (comprehension_v0, LLM seam)",
    REFUSAL_QUOTE_NOT_IN_SOURCE: "the model reader (comprehension_v0, LLM seam)",
    REFUSAL_MODEL_UNREACHABLE: "the model adapter (LLM seam) — and it will be "
                               "DEGENERATE on arrival for the same reason "
                               "source_unreachable is, if outages keep raising",
}

#: Declared, advertised, and impossible to record.
REASONS_DEGENERATE: Mapping[str, str] = {
    REFUSAL_SOURCE_UNREACHABLE: (
        "a real refusal reason that NO origin record can ever carry. The "
        "store-unreachable path RAISES (PolicyStoreUnreachableError), and a "
        "raising step writes no origin record at all — execute_pipeline records "
        "the stop, not an output. Exactly the shape of environment_fault, which "
        "is derived from this reason and its twin. RESOLVED 2026-08-13: the OPEN "
        "question here was whether a producer should keep ADVERTISING a reason "
        "it cannot record. It should not, and policy_lookup_v0 no longer does — "
        "a possible-list naming it told a renderer 'this lookup could have told "
        "you the store was unreachable', which is a sentence no record could "
        "ever be the evidence for. The token is NOT deleted: it stays the "
        "machine-readable reason on the exception and reaches a reader through "
        "L-2's RunStopped node, which is where 'was this our fault' belongs. It "
        "stays classified degenerate because that is still true of RECORDS — "
        "which is what this whole classification is about."
    ),
}

#: Written by at least one shipped producer, on at least one path. The
#: enforcement test **runs the producers and checks** — so this list going
#: stale is a red gate, not a stale comment.
FIELDS_WRITTEN_TODAY: Tuple[str, ...] = SPINE + (
    FIELD_BASIS,
    FIELD_SOURCE_VERSION,
    FIELD_SOURCE_IN_FORCE_FROM,
    FIELD_SOURCE_IN_FORCE_TO,
)

#: Declared for a producer that does not exist yet, each naming the one that
#: will write it. A field may not sit here anonymously: *"someone might need
#: it"* is how a union stops meaning anything.
FIELDS_RESERVED: Mapping[str, str] = {
    FIELD_ORIGIN_PARTY: "a party-assertion producer (asserted_by_party)",
    FIELD_ORIGIN_PARTY_PHRASE: "a party-assertion producer (asserted_by_party)",
    FIELD_EXPECTED_BASIS: "the model reader (comprehension_v0, LLM seam)",
    FIELD_QUOTE: "the model reader (comprehension_v0, LLM seam)",
    FIELD_CLAIMED_QUOTE: "the model reader (comprehension_v0, LLM seam)",
    FIELD_QUOTE_VERIFIED: "the model reader (comprehension_v0, LLM seam)",
    FIELD_QUOTE_OFFSETS: "the model reader (comprehension_v0, LLM seam)",
    FIELD_MODEL_ID: "the model adapter (LLM seam)",
    FIELD_MODEL_VERSION: "the model adapter (LLM seam)",
    FIELD_PROMPT_IRI: "the model adapter (LLM seam)",
    FIELD_PROMPT_VERSION: "the model adapter (LLM seam)",
    FIELD_TEMPERATURE: "the model adapter (LLM seam)",
    FIELD_REQUEST_KEY: "the model adapter (LLM seam)",
    FIELD_RECORDED: "the model adapter (LLM seam)",
}

#: Written on every record, but whose **informative value is unreachable** —
#: worse than an unwritten field, because it looks live and reads as evidence.
FIELDS_DEGENERATE: Mapping[str, str] = {
    FIELD_ENVIRONMENT_FAULT: (
        "always False, and structurally so. It is derived from "
        "ENVIRONMENT_FAULT_REASONS, and BOTH of those reasons — "
        "model_unreachable and source_unreachable — are on RAISING paths. A "
        "raising step writes no origin record at all (execute_pipeline records "
        "the stop, not an output), so no record that carries this field can "
        "ever have been produced by an outage. A renderer must take 'was this "
        "our fault' from L-2's RunStopped node, NEVER from this field. Deleted "
        "the day a non-raising outage exists; until then it is pinned."
    ),
}

#: Printed by a Record. Everything else in the union is **structural** — read
#: to walk the graph or to branch, never rendered.
FIELDS_PRINTED: Tuple[str, ...] = (
    FIELD_ORIGIN_METHOD_PHRASE,
    FIELD_SOURCE_IDENTITY_PHRASE,
    FIELD_ORIGIN_PARTY_PHRASE,
    FIELD_QUESTION,
    FIELD_REFUSAL_DETAIL,
    FIELD_QUOTE,
    FIELD_SOURCE_VERSION,
    FIELD_SOURCE_IN_FORCE_FROM,
    FIELD_SOURCE_IN_FORCE_TO,
)

#: Read, never rendered. ``source_datastate`` is the one that bites: it holds a
#: DataState **IRI**, it is on every record both shipped producers write, and
#: printing it is a G6 leak. Its prose counterpart already exists and is
#: ``source_identity_phrase``. The refusal **tokens** are here for the same
#: reason — code branches on them, ``refusal_detail`` is what a reader is shown.
FIELDS_STRUCTURAL: Tuple[str, ...] = tuple(
    f for f in ORIGIN_UNION if f not in FIELDS_PRINTED
)


class OriginContractError(ValueError):
    """A record does not satisfy the origin contract."""


#: Opaque tag every origin-record DataState carries, whoever produces it.
#: **One tag, deliberately.** It moved here from ``policy_lookup_v0`` the
#: moment a second producer needed it: two producers with two tags would give
#: their origin DataStates two different shapes, and a renderer could no longer
#: treat "the origin of this value" as one thing. Opaque is correct rather than
#: a shortcut — the union above is closed by agreement and not frozen, so a
#: record shape pinned today would pin a guess — and it is safe for the reason
#: ``DECISION_SHAPED_CATEGORIES`` exists: an origin record is never consumed by
#: a capacity that compares it against a limit. The **value** always carries a
#: real shape; that one is never opaque.
ORIGIN_SHAPE_TAG = "origin.record.v0"


def origin_record_iri(value_datastate_iri: str) -> str:
    """The origin-record DataState paired with ``value_datastate_iri``.

    **Per value, never one shared type.** The executor holds one value per
    DataState IRI per run, so a shared origin type would have the second
    producer in a run displace the first's provenance and the grounding
    graph would wire the wrong producer.

    Suffix is ``_origin`` and not ``.origin``: DataState names are
    ``<realm>.<name>`` and a second dot is rejected at registration.
    """
    return value_datastate_iri + "_origin"


def assert_printable_phrase(phrase: Any, field_name: str) -> None:
    """A phrase the Record prints must be prose, never an identifier.

    The rule itself lives in :mod:`mindsos_capacity.printable` because
    ``register_capacity`` enforces the same one on a capacity's
    ``printable_phrase`` and core cannot import from ``builtins/``. This
    wrapper exists so an origin-contract violation still raises
    :class:`OriginContractError`; the message is unchanged.
    """
    problem = printable_phrase_problem(phrase, field_name)
    if problem is not None:
        raise OriginContractError(problem)


def build_origin_record(
    *,
    producer_kind: str,
    origin_method: str,
    source_identity_phrase: str,
    source_datastate: Optional[str],
    question: str,
    admitted: bool,
    supplied_fields: Sequence[str],
    possible_refusal_reasons: Sequence[str],
    refusal_reason: Optional[str] = None,
    refusal_detail: Optional[str] = None,
    **producer_fields: Any,
) -> Dict[str, Any]:
    """Assemble one origin record, validating the contract as it goes.

    Every spine field is written. ``supplied_fields`` names the
    producer-declared fields this producer *always* populates, so the
    renderer can tell a normal absence from a defect. ``environment_fault``
    is **derived** from the reason rather than passed, so a producer cannot
    mislabel its own outage as a finding about the customer's case.
    """
    if producer_kind not in PRODUCER_KINDS:
        raise OriginContractError(
            f"producer_kind must be one of {PRODUCER_KINDS!r}, got {producer_kind!r}"
        )
    if origin_method not in ORIGIN_METHODS:
        raise OriginContractError(
            f"origin_method must be one of {ORIGIN_METHODS!r}, got {origin_method!r}"
        )
    if refusal_reason is not None and refusal_reason not in REFUSAL_REASONS:
        raise OriginContractError(
            f"refusal_reason must be one of {REFUSAL_REASONS!r}, got {refusal_reason!r}"
        )
    if refusal_reason is not None and not str(refusal_detail or "").strip():
        # A refusal with no prose is unrenderable. The TOKEN is for branching;
        # ``refusal_detail`` is the only thing a reader is ever shown, and it
        # was optional — so a producer could refuse and leave a Record with
        # nothing to say. Every shipped producer already supplies one, so this
        # pins the contract rather than changing it.
        raise OriginContractError(
            f"a refusal must carry prose: refusal_reason={refusal_reason!r} was "
            f"given with no refusal_detail. The token branches; the detail is "
            f"what the Record prints."
        )
    unknown = sorted(f for f in producer_fields if f not in PRODUCER_DECLARED)
    if unknown:
        raise OriginContractError(
            f"{unknown!r} are not in the origin union. The union is closed by "
            f"agreement — a new field is a negotiation between producers, not a "
            f"local addition."
        )
    unreachable = sorted(r for r in possible_refusal_reasons if r not in REFUSAL_REASONS)
    if unreachable:
        raise OriginContractError(
            f"possible_refusal_reasons names {unreachable!r}, which are not in the "
            f"global reason vocabulary."
        )
    if refusal_reason is not None and refusal_reason not in possible_refusal_reasons:
        raise OriginContractError(
            f"this producer emitted {refusal_reason!r} but did not declare it as one "
            f"of its possible reasons {sorted(possible_refusal_reasons)!r}. The "
            f"renderer distinguishes 'could never say this' from 'happened not to'."
        )
    undeclared = sorted(f for f in supplied_fields if f not in PRODUCER_DECLARED)
    if undeclared:
        raise OriginContractError(
            f"supplied_fields names {undeclared!r}, which are not "
            f"producer-declared fields of the union."
        )
    assert_printable_phrase(source_identity_phrase, FIELD_SOURCE_IDENTITY_PHRASE)
    party_phrase = producer_fields.get(FIELD_ORIGIN_PARTY_PHRASE)
    if party_phrase is not None:
        assert_printable_phrase(party_phrase, FIELD_ORIGIN_PARTY_PHRASE)

    record: Dict[str, Any] = {
        FIELD_PRODUCER_KIND: producer_kind,
        FIELD_SUPPLIED_FIELDS: list(supplied_fields),
        FIELD_ORIGIN_METHOD: origin_method,
        FIELD_ORIGIN_METHOD_PHRASE: ORIGIN_METHOD_PHRASES[origin_method],
        FIELD_SOURCE_IDENTITY_PHRASE: source_identity_phrase,
        FIELD_SOURCE_DATASTATE: source_datastate,
        FIELD_QUESTION: question,
        FIELD_ADMITTED: bool(admitted),
        FIELD_REFUSAL_REASON: refusal_reason,
        FIELD_REFUSAL_DETAIL: refusal_detail,
        FIELD_ENVIRONMENT_FAULT: refusal_reason in ENVIRONMENT_FAULT_REASONS,
        FIELD_POSSIBLE_REFUSAL_REASONS: list(possible_refusal_reasons),
    }
    record.update(producer_fields)
    return record


def missing_declared_fields(record: Mapping[str, Any]) -> List[str]:
    """Fields the record's producer promised but did not supply.

    The renderer's *never infer from absence* rule made checkable: inside
    ``supplied_fields`` a missing value is a defect, outside it normal.
    """
    return [
        name
        for name in record.get(FIELD_SUPPLIED_FIELDS, ())
        if record.get(name) is None
    ]


# ── Scope-aware registry walks ─────────────────────────────────────────

#: Families whose inputs are compared, ordered or tested against a limit.
DECISION_SHAPED_CATEGORIES = frozenset({"decision", "comparator", "predicate"})

_OPAQUE_KIND = "opaque"


def _declarations(capacity_layer, metagraph) -> Iterable[Tuple[str, Any]]:
    """``(iri, declaration)`` from a metagraph's capacity index.

    The index stores ``(Node, Graph, declaration)`` tuples; reading the
    entry itself yields a tuple with no ``outputs``, which silently
    disables any guard written against it. Bare declarations are accepted
    too so a future index shape cannot re-break this quietly.
    """
    index = capacity_layer._capacity_index.get(metagraph.metagraph_id, {})
    for iri, entry in index.items():
        declaration = entry[2] if isinstance(entry, tuple) and len(entry) >= 3 else entry
        yield iri, declaration


def metagraphs_in_scope(capacity_layer, user_id: Optional[str] = None) -> List[Any]:
    """Every metagraph a capacity in this scope could resolve against.

    Global always; the user's Local as well when one is named. **A guard
    that reads only Global passes silently the moment registration moves
    Local** — which is exactly the configuration a Local-first trial
    chooses, so every guard here is scope-aware by construction.
    """
    metagraphs = [capacity_layer.global_metagraph()]
    if user_id is not None:
        local = capacity_layer._locals.get(user_id)
        if local is not None:
            metagraphs.append(local)
    return metagraphs


def _decision_shaped(capacity_layer, user_id, attribute, datastate_iri):
    found: List[str] = []
    for metagraph in metagraphs_in_scope(capacity_layer, user_id):
        for iri, declaration in _declarations(capacity_layer, metagraph):
            try:
                category, _ = parse_capacity_iri(iri)
            except Exception:  # pragma: no cover — a malformed IRI is not ours
                continue
            if category not in DECISION_SHAPED_CATEGORIES:
                continue
            if datastate_iri in tuple(getattr(declaration, attribute, ()) or ()):
                found.append(iri)
    return sorted(set(found))


def decision_consumers_of(capacity_layer, datastate_iri, *, user_id=None) -> List[str]:
    """Decision-shaped capacities consuming ``datastate_iri``, across scope."""
    return _decision_shaped(capacity_layer, user_id, "inputs", datastate_iri)


def decision_producers_of(capacity_layer, datastate_iri, *, user_id=None) -> List[str]:
    """Decision-shaped capacities producing ``datastate_iri``, across scope."""
    return _decision_shaped(capacity_layer, user_id, "outputs", datastate_iri)


def opaque_into_decision(capacity_layer, *, user_id=None) -> List[Tuple[str, str]]:
    """``(datastate_iri, capacity_iri)`` for every opaque value a
    decision-shaped capacity consumes.

    **An opaque-shaped value compared against a limit is a defect every
    time.** There is no legitimate case for it, and the failure is not a
    crash but a *confidently wrong answer* — a Record comparing ``"47
    days"`` against ``30`` and getting it wrong.

    Order-independent by construction: it walks the registry rather than
    firing at one registration, so it catches the pairing whichever side
    registered first. **Call it from the test that boots the whole Skill**,
    not from a package-scoped test — the pairing spans lanes.
    """
    offenders: List[Tuple[str, str]] = []
    for metagraph in metagraphs_in_scope(capacity_layer, user_id):
        # ``DataState.to_properties`` flattens the descriptor onto the node
        # as ``shape_kind`` / ``shape_elem`` / ``shape_opaque_tag`` — there
        # is no nested "shape" mapping to read.
        kinds: Dict[str, Any] = {}
        for graph in metagraph.graphs.values():
            for node in graph.nodes.values():
                kind = (node.properties or {}).get("shape_kind")
                if kind is not None:
                    kinds[node.node_id] = kind
        for iri, declaration in _declarations(capacity_layer, metagraph):
            try:
                category, _ = parse_capacity_iri(iri)
            except Exception:  # pragma: no cover
                continue
            if category not in DECISION_SHAPED_CATEGORIES:
                continue
            for consumed in tuple(getattr(declaration, "inputs", ()) or ()):
                if kinds.get(consumed) == _OPAQUE_KIND:
                    offenders.append((consumed, iri))
    return sorted(set(offenders))


__all__ = [
    "BASES", "BASIS_INFERRED", "BASIS_STATED",
    "DECISION_SHAPED_CATEGORIES", "ENVIRONMENT_FAULT_REASONS",
    "ORIGIN_ASSERTED_BY_PARTY", "ORIGIN_METHODS", "ORIGIN_METHOD_PHRASES",
    "ORIGIN_READ_BY_MODEL", "ORIGIN_READ_FROM_SOURCE", "ORIGIN_UNION",
    "OriginContractError",
    "PRODUCER_DECLARED", "PRODUCER_DOCUMENT_READING", "PRODUCER_KINDS",
    "PRODUCER_POLICY_LOOKUP", "PRODUCER_STRUCTURED_INGEST",
    "REFUSAL_FIELD_ABSENT", "REFUSAL_MALFORMED_RESPONSE",
    "REFUSAL_MODEL_DECLINED", "REFUSAL_MODEL_UNREACHABLE",
    "REFUSAL_NO_SOURCE_IN_FORCE", "REFUSAL_QUOTE_NOT_IN_SOURCE",
    "FIELDS_DEGENERATE", "FIELDS_PRINTED", "FIELDS_RESERVED",
    "REASONS_DEGENERATE", "REASONS_EMITTED_TODAY", "REASONS_RESERVED",
    "FIELDS_STRUCTURAL", "FIELDS_WRITTEN_TODAY",
    "REFUSAL_REASONS", "REFUSAL_SOURCE_UNREACHABLE",
    "REFUSAL_VALUE_NOT_COERCIBLE", "SPINE",
    "ORIGIN_SHAPE_TAG",
    "assert_printable_phrase", "build_origin_record",
    "decision_consumers_of", "decision_producers_of",
    "metagraphs_in_scope", "missing_declared_fields",
    "opaque_into_decision", "origin_record_iri",
]
