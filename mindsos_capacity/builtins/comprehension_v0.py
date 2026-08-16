"""Comprehension family v0 — reading a document with an external model.

The L3 half of the external-model seam. ``mindsos_llm`` is transport,
recording and replay; **this module is the cognition**: it asks, it checks
what came back against the source, and it declines when the check fails.
The model reads. It does not decide, and §"The model cannot decide" below
makes that mechanical rather than aspirational.

The record shape lives in :mod:`origin_v0`, not here — a policy lookup
produces origin too and never touches a model, so the shape cannot belong
to this family. This module is one **producer** of that shape:
``PRODUCER_DOCUMENT_READING``.

**One reader per extracted value, not one general extractor.** A single
"read the whole document" capacity would produce one opaque payload: the
finder would have nothing to compose through and a Decision Record nothing
to cite. :func:`build_reader` is therefore a factory — a Skill registers
one reader per value it needs. Note the shipped executor holds one value
per DataState IRI, so two readers producing "a date" must produce two
*different* date types.

**Every reading is checked against the source.** The model must return a
verbatim quote for the value it reports. The body locates that quote in the
source text itself (:func:`locate_quote`); if it is not there, the reading
is refused. A fabricated value therefore becomes a refusal by construction.

**Every reading is coerced to its declared shape.** A day count that comes
back as *"about seven weeks"* is a reading failure, refused in the same
record as the quote that caused it — not a string handed downstream for a
threshold to compare against a number and get confidently wrong.

**Uncertainty is structural, never a self-reported number.** What is
recorded is what MindsOS established: whether the quote was found, where,
and whether the model reported the value as *stated* in the source or
*inferred* from its surroundings. A model-supplied confidence is another
output of the process under question, so none is stored as evidence.

**Declining does not use ``NeedsInput``.** It short-circuits output
validation, so a reader raising it would leave *no* node in the grounding
graph explaining why the value is missing. A reader instead returns
``{value: None, record: {...refusal...}}``, so the refusal is written into
the run graph like any other output, and the escalation is raised by the
decision step that finds it cannot evaluate its condition.

**A transport failure RAISES; it is not a refusal.** *"The document does
not say"* is a finding about the customer's case and belongs in their
refusal list. *"Our reading service was down"* is our outage and must
never appear there (§7A). The seam originally made it an in-band
``model_unreachable`` refusal because a raising member reader then
destroyed the whole claim's Record — that motivation DIED at ADR-0201
am-6: today a raising member STOPS IN PLACE, its siblings run, and the
fold stops ``partial_domain``. So the outage travels the same road the
policy-store outage already travels, no record carries it, and
``environment_fault`` stays degenerate. (Coordination §85 Q3, adopted
§86; the manual's §5.5 is overruled by it.)

**The ONE exception caught here is a bad ANSWER, not a bad environment.**
:class:`~mindsos_capacity.llm.exceptions.MalformedResponse` means the
model replied and its reply could not be decoded — a finding about the
answer, so it becomes a ``malformed_response`` refusal carrying the raw
words. There is no catch-all: budget exhaustion, a replay miss, a
transport contract violation and an outage all propagate, and each is a
stop with its own meaning.

**The model cannot decide.** :func:`register_reader` refuses at
registration time if the DataState a reader would produce is also produced
by any decision-shaped capacity — checked across **Global and the caller's
Local**, because a guard reading only Global passes silently the moment
registration moves Local.

**Global or Local.** ``register_reader(session=...)`` registers into the
caller's Local metagraph; without a session it registers Global. Local
first is the Decision Records trial: nothing enters the Global catalog
until the shape is proven. Note that today ``pipeline._view_for`` returns
Global *or* Local and never both, so a Local trial means the **whole**
path must be Local until the two-tier union view lands.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from ..bootstrap import ensure_datastate_graph
from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..exceptions import CapacityRegistrationError
from ..identifiers import CATEGORY_COMPREHENSION, datastate_iri
from ..llm.exceptions import MalformedResponse
from .origin_v0 import (
    BASES,
    BASIS_INFERRED,
    BASIS_STATED,
    FIELD_BASIS,
    FIELD_CLAIMED_QUOTE,
    FIELD_EXPECTED_BASIS,
    FIELD_MODEL_ID,
    FIELD_MODEL_VERSION,
    FIELD_ORIGIN_PARTY,
    FIELD_ORIGIN_PARTY_PHRASE,
    FIELD_PROMPT_IRI,
    FIELD_PROMPT_VERSION,
    FIELD_QUOTE,
    FIELD_QUOTE_OFFSETS,
    FIELD_QUOTE_VERIFIED,
    FIELD_RECORDED,
    FIELD_REQUEST_KEY,
    FIELD_TEMPERATURE,
    ORIGIN_ASSERTED_BY_PARTY,
    ORIGIN_READ_BY_MODEL,
    ORIGIN_READ_FROM_SOURCE,
    PRODUCER_DOCUMENT_READING,
    REFUSAL_FIELD_ABSENT,
    REFUSAL_MALFORMED_RESPONSE,
    REFUSAL_MODEL_DECLINED,
    REFUSAL_QUOTE_NOT_IN_SOURCE,
    REFUSAL_VALUE_NOT_COERCIBLE,
    assert_printable_phrase,
    build_origin_record,
    decision_producers_of,
    origin_record_iri,
)

#: Which party may have put the fact into the world.
ORIGIN_PARTIES = (ORIGIN_READ_FROM_SOURCE, ORIGIN_ASSERTED_BY_PARTY)

#: The reasons a document reading could ever emit. The vocabulary is global
#: and closed; this is the subset this producer can reach, so a renderer can
#: tell "a reader would never say no_source_in_force" from "it happened not
#: to".
READER_POSSIBLE_REFUSAL_REASONS: Tuple[str, ...] = (
    REFUSAL_MODEL_DECLINED,
    REFUSAL_FIELD_ABSENT,
    REFUSAL_QUOTE_NOT_IN_SOURCE,
    REFUSAL_MALFORMED_RESPONSE,
    REFUSAL_VALUE_NOT_COERCIBLE,
)
# ``model_unreachable`` is deliberately NOT here, and its absence is the
# ADR-0207 am-3 rule applied a second time: the outage path RAISES, a
# raising step writes no origin record, so no record of this producer
# could ever carry that reason. Advertising it would tell a renderer
# "this reader could have told you the model was unreachable" — a
# sentence no record can be the evidence for. The token is not deleted:
# it stays the machine-readable reason on ``LLMCallFailed`` and reaches a
# reader through L-2's ``RunStopped`` node.

#: How much of an undecodable answer a refusal keeps. Long enough to see
#: what shape came back, short enough that a page stays a page.
RAW_ANSWER_LIMIT = 240


def _bounded(raw: Any) -> str:
    """The model's raw answer, printable and length-bounded."""
    text = raw if isinstance(raw, str) else repr(raw)
    if len(text) <= RAW_ANSWER_LIMIT:
        return text
    return text[:RAW_ANSWER_LIMIT] + f"… ({len(text)} characters in all)"


#: What a document reading ALWAYS supplies. Everything else in the union is
#: another producer's, and its absence here is normal rather than a defect.
READER_SUPPLIED_FIELDS: Tuple[str, ...] = (
    FIELD_ORIGIN_PARTY,
    FIELD_ORIGIN_PARTY_PHRASE,
    FIELD_EXPECTED_BASIS,
    FIELD_QUOTE_VERIFIED,
)


# ── Quote location ─────────────────────────────────────────────────────


def _normalise(text: str) -> Tuple[str, List[int]]:
    """Whitespace-collapsed text plus a map back to original offsets.

    Runs of whitespace become one space so a quote differing from the
    source only in line wrapping still verifies, while returned offsets
    still point into the untouched source — the Record quotes the document,
    not a normalised copy of it.
    """
    out: List[str] = []
    index: List[int] = []
    in_space = False
    for pos, ch in enumerate(text):
        if ch.isspace():
            if not in_space and out:
                out.append(" ")
                index.append(pos)
            in_space = True
            continue
        in_space = False
        out.append(ch)
        index.append(pos)
    while out and out[-1] == " ":
        out.pop()
        index.pop()
    return "".join(out), index


def locate_quote(source_text: str, quote: str) -> Optional[Tuple[int, int]]:
    """``(start, end)`` of ``quote`` inside ``source_text``, or ``None``.

    Exact match first, then whitespace-insensitive. Case is significant — a
    reading that changes the casing of the source is not a quotation of it.
    ``None`` means the model produced words the document does not contain,
    which is the whole point of asking for a quote.
    """
    if not quote:
        return None
    exact = source_text.find(quote)
    if exact >= 0:
        return (exact, exact + len(quote))
    norm_source, index = _normalise(source_text)
    norm_quote, _ = _normalise(quote)
    if not norm_quote:
        return None
    hit = norm_source.find(norm_quote)
    if hit < 0:
        return None
    return (index[hit], index[hit + len(norm_quote) - 1] + 1)


# ── Coercion to the declared shape ─────────────────────────────────────

class _NotCoercible(Exception):
    """The model's value will not fit the DataState's declared shape."""


class SourceTextUnavailable(RuntimeError):
    """A reader was asked to read a document that is absent or empty.

    ``str(exc)`` is FIXED PROSE: ``execute_pipeline`` writes it onto L-2's
    ``RunStopped`` node and a Decision Record prints it, so it names no
    DataState, no IRI and no internal token (the rule
    ``mindsos_capacity.llm.exceptions`` states for the client's errors,
    and the reason ``PolicyStoreUnreachableError`` states it too).

    A raise rather than a refusal: nothing was read because nothing
    arrived, which is a fault in the run that routed here, and our faults
    do not pad a customer's refusal list (§7A).
    """

    MESSAGE = "no document was supplied to read"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


def coerce_to_shape(value: Any, shape: Optional[ShapeDescriptor]) -> Any:
    """Fit ``value`` to ``shape``, or raise :class:`_NotCoercible`.

    Only scalar shapes are coerced; an ``opaque`` shape declares that there
    is nothing to check against, so the value passes through untouched.
    That is the honest behaviour and also the hazard — an opaque value
    consumed by a decision capacity is a defect every time, which is why
    ``origin_v0.opaque_into_decision`` exists.
    """
    if shape is None or shape.kind != "scalar" or value is None:
        return value
    elem = shape.elem
    try:
        if elem == "int":
            if isinstance(value, bool):
                raise _NotCoercible("a boolean is not a count")
            if isinstance(value, float) and value != int(value):
                raise _NotCoercible("a fractional value is not a count")
            return int(str(value).strip()) if isinstance(value, str) else int(value)
        if elem == "float":
            return float(str(value).strip()) if isinstance(value, str) else float(value)
        if elem == "bool":
            if isinstance(value, bool):
                return value
            text = str(value).strip().lower()
            if text in ("true", "yes"):
                return True
            if text in ("false", "no"):
                return False
            raise _NotCoercible(f"{value!r} is not a yes/no answer")
        if elem == "str":
            if isinstance(value, (dict, list)):
                raise _NotCoercible("a structure is not a piece of text")
            return str(value)
    except _NotCoercible:
        raise
    except (TypeError, ValueError) as exc:
        raise _NotCoercible(str(exc)) from exc
    return value


# ── DataStates for one reader ──────────────────────────────────────────


def reader_datastates(
    *,
    value_datastate_iri: str,
    value_description: str,
    value_shape: Optional[ShapeDescriptor] = None,
) -> List[DataState]:
    """The value DataState and its paired origin-record DataState."""
    short = value_datastate_iri.split(":", 1)[-1]
    return [
        DataState(
            name=short,
            shape=value_shape or ShapeDescriptor.opaque(short),
            description=value_description,
            provenance_category=CATEGORY_COMPREHENSION,
        ),
        DataState(
            name=short + "_origin",
            shape=ShapeDescriptor.opaque(short + "_origin"),
            description=(
                "Where " + value_description[:1].lower() + value_description[1:]
                + " came from: the document quoted, where the quote sits in it, the "
                "model and prompt version that read it, and — when the value is "
                "absent — why it was refused."
            ),
            provenance_category=CATEGORY_COMPREHENSION,
        ),
    ]


# ── The body ───────────────────────────────────────────────────────────


def _make_impl(
    *,
    source_datastate_iri: str,
    value_datastate_iri: str,
    record_datastate_iri: str,
    prompt_iri: str,
    prompt_version: int,
    field_name: str,
    question: str,
    origin_party: str,
    origin_party_phrase: str,
    source_identity_phrase: str,
    expected_basis: str,
    value_shape: Optional[ShapeDescriptor],
    extraction_schema: Optional[Mapping[str, Any]],
):
    def _record(reason=None, detail=None, response=None, admitted=False, **extra):
        resp = dict(response or {})
        fields = {
            FIELD_ORIGIN_PARTY: origin_party,
            FIELD_ORIGIN_PARTY_PHRASE: origin_party_phrase,
            FIELD_EXPECTED_BASIS: expected_basis,
            FIELD_QUOTE_VERIFIED: bool(extra.pop("quote_verified", False)),
            FIELD_MODEL_ID: resp.get("model_id"),
            FIELD_MODEL_VERSION: resp.get("model_version"),
            FIELD_PROMPT_IRI: resp.get("prompt_iri", prompt_iri),
            FIELD_PROMPT_VERSION: resp.get("prompt_version", prompt_version),
            FIELD_TEMPERATURE: resp.get("temperature"),
            FIELD_REQUEST_KEY: resp.get("request_key"),
            FIELD_RECORDED: resp.get("recorded"),
        }
        fields.update(extra)
        return build_origin_record(
            producer_kind=PRODUCER_DOCUMENT_READING,
            origin_method=ORIGIN_READ_BY_MODEL,
            source_identity_phrase=source_identity_phrase,
            source_datastate=source_datastate_iri,
            question=question,
            admitted=admitted,
            supplied_fields=READER_SUPPLIED_FIELDS,
            possible_refusal_reasons=READER_POSSIBLE_REFUSAL_REASONS,
            refusal_reason=reason,
            refusal_detail=detail,
            **fields,
        )

    def _refuse(reason, detail, response=None, **extra):
        return {
            value_datastate_iri: None,
            record_datastate_iri: _record(
                reason=reason, detail=detail, response=response, admitted=False, **extra
            ),
        }

    def _impl(**kwargs: Any) -> Dict[str, Any]:
        context = kwargs.get("context")
        source_text = kwargs.get(source_datastate_iri)
        llm = getattr(context, "llm", None)
        if llm is None:
            # Unreachable through L4 dispatch, which refuses to run an
            # LLM-category capacity with no client bound. Guarded anyway so
            # a direct L3 invoke fails loudly instead of quietly reporting
            # "the document did not say".
            raise CapacityRegistrationError(
                f"comprehension reader for {value_datastate_iri!r} was invoked with "
                f"no LLM on the context. A missing client is a deployment error, "
                f"not a don't-know."
            )
        if not isinstance(source_text, str) or not source_text.strip():
            # No document arrived. That is OUR routing, not a finding about
            # the customer's case, so it must not become a refusal in their
            # list (§7A) — and it must not be called ``malformed_response``,
            # which now means one specific thing: the model replied and its
            # reply would not decode. It raises, which under ADR-0201 am-6
            # stops this member in place and names the stop on the page.
            raise SourceTextUnavailable()

        # NO catch-all. Every transport failure propagates with its own
        # meaning: ``LLMCallFailed`` (our outage, §85 Q3),
        # ``LLMCallBudgetExceeded`` (our ceiling), ``RecordedResponseMiss``
        # (our recorded set), ``TransportContractError`` (our deployment).
        # None of them is a fact about this document, and a stop says so.
        try:
            response = llm.read(
                prompt_iri=prompt_iri,
                prompt_version=prompt_version,
                source_text=source_text,
                extraction_schema=extraction_schema,
            )
        except MalformedResponse as exc:
            # The one failure that IS about the answer: the model replied
            # and the reply would not decode.
            #
            # **The raw answer is retained, and it is on the printed
            # detail deliberately.** ``refusal_detail`` is what a Record
            # shows for a refusal, and a refusal that says only "could not
            # be read" asks the reader to take our word for it — the S-7
            # discipline is to keep the words. This does NOT contradict
            # the fixed-prose rule the client's exceptions follow: that
            # rule is about text a THIRD-PARTY LIBRARY wrote, which nobody
            # here has read. This is the model's own answer about the
            # customer's document, which is the exact thing under audit.
            # Bounded, because a model can return a great deal of it.
            return _refuse(
                REFUSAL_MALFORMED_RESPONSE,
                "the model's answer could not be read. It returned: "
                + _bounded(exc.raw),
            )

        # No ``isinstance(response, Mapping)`` branch: the client's
        # ``decode_response`` already guarantees a mapping or raises
        # (S-2 lives there, where the failure is typed and tested). A
        # defensive re-check here would be a second decoder that no test
        # can redden.
        if response.get("declined"):
            return _refuse(
                REFUSAL_MODEL_DECLINED,
                str(response.get("decline_reason") or "the model declined to read this"),
                response,
            )

        field = None
        for candidate in response.get("fields") or []:
            if isinstance(candidate, Mapping) and candidate.get("name") == field_name:
                field = candidate
                break
        if field is None:
            return _refuse(
                REFUSAL_FIELD_ABSENT,
                f"the reading carried no field named {field_name!r}",
                response,
            )

        quote = field.get("quote")
        offsets = locate_quote(source_text, quote) if isinstance(quote, str) else None
        if offsets is None:
            # The reported words are not in the document. The fabrication
            # catch, and it is a refusal rather than a warning.
            return _refuse(
                REFUSAL_QUOTE_NOT_IN_SOURCE,
                "the quote supporting this value does not appear in the document "
                "it was said to come from",
                response,
                **{FIELD_CLAIMED_QUOTE: quote if isinstance(quote, str) else None},
            )

        try:
            value = coerce_to_shape(field.get("value"), value_shape)
        except _NotCoercible as exc:
            return _refuse(
                REFUSAL_VALUE_NOT_COERCIBLE,
                f"the document gave {field.get('value')!r}, which is not usable here ({exc})",
                response,
                **{
                    FIELD_QUOTE: source_text[offsets[0]:offsets[1]],
                    FIELD_CLAIMED_QUOTE: quote,
                    FIELD_QUOTE_OFFSETS: [offsets[0], offsets[1]],
                    "quote_verified": True,
                },
            )

        basis = field.get("basis")
        return {
            value_datastate_iri: value,
            record_datastate_iri: _record(
                response=response,
                admitted=True,
                quote_verified=True,
                **{
                    FIELD_QUOTE: source_text[offsets[0]:offsets[1]],
                    FIELD_CLAIMED_QUOTE: quote,
                    FIELD_QUOTE_OFFSETS: [offsets[0], offsets[1]],
                    FIELD_BASIS: basis if basis in BASES else BASIS_INFERRED,
                },
            ),
        }

    return _impl


# ── Builder + registration ─────────────────────────────────────────────


def build_reader(
    *,
    name: str,
    source_datastate_iri: str,
    value_datastate_iri: str,
    prompt_iri: str,
    prompt_version: int,
    field_name: str,
    question: str,
    description: str,
    origin_party_phrase: str,
    source_identity_phrase: str,
    expected_basis: str,
    origin_party: str = ORIGIN_ASSERTED_BY_PARTY,
    value_shape: Optional[ShapeDescriptor] = None,
    extraction_schema: Optional[Mapping[str, Any]] = None,
) -> Capacity:
    """One reader: source document in, one typed value + its origin out.

    **Two phrases, not one.** ``origin_party_phrase`` names *who asserted
    it* ("the customer"); ``source_identity_phrase`` names *what was
    consulted* ("their submission email"). They were one welded string
    until a policy lookup — which consults an authority and has no
    asserting party — showed the field was doing two jobs. The renderer
    composes them; one string never allowed that.

    ``question`` is the plain-language thing being read ("the date the item
    was purchased"). ``expected_basis`` says whether it is supposed to be
    *stated* in the document or *inferred* from it. Both are registered, so
    a Record's wording ships with the definition and cannot drift from what
    ran — and both survive a refusal, because the escalation has to name
    what was missing and where it should have been.

    ``value_shape`` drives coercion. Leave it opaque and nothing is
    checked, which is legitimate for genuinely opaque values and a defect
    for anything a decision capacity will compare.
    """
    if origin_party not in ORIGIN_PARTIES:
        raise CapacityRegistrationError(
            f"origin_party must be one of {ORIGIN_PARTIES!r}, got {origin_party!r}"
        )
    if expected_basis not in BASES:
        raise CapacityRegistrationError(
            f"expected_basis must be one of {BASES!r}, got {expected_basis!r}"
        )
    for phrase, label in (
        (origin_party_phrase, "origin_party_phrase"),
        (source_identity_phrase, "source_identity_phrase"),
    ):
        assert_printable_phrase(phrase, label)
    return Capacity(
        name=name,
        category=CATEGORY_COMPREHENSION,
        inputs=(source_datastate_iri,),
        outputs=(value_datastate_iri, origin_record_iri(value_datastate_iri)),
        implementation=_make_impl(
            source_datastate_iri=source_datastate_iri,
            value_datastate_iri=value_datastate_iri,
            record_datastate_iri=origin_record_iri(value_datastate_iri),
            prompt_iri=prompt_iri,
            prompt_version=prompt_version,
            field_name=field_name,
            question=question,
            origin_party=origin_party,
            origin_party_phrase=origin_party_phrase,
            source_identity_phrase=source_identity_phrase,
            expected_basis=expected_basis,
            value_shape=value_shape,
            extraction_schema=extraction_schema,
        ),
        description=description,
    )


def assert_not_an_outcome(capacity_layer, value_datastate_iri: str, *, session=None) -> None:
    """Refuse a reader whose output a decision-shaped capacity produces.

    The mechanical form of "the model reads, it does not decide": a reader
    may feed a decision, never stand in for one. Checked across **Global
    and the caller's Local** — a guard reading only Global passes silently
    the moment registration moves Local, which is exactly the configuration
    a Local-first trial chooses.
    """
    user_id = getattr(session, "user_id", None) if session is not None else None
    offenders = decision_producers_of(capacity_layer, value_datastate_iri, user_id=user_id)
    if offenders:
        raise CapacityRegistrationError(
            f"comprehension reader would produce {value_datastate_iri!r}, which is "
            f"already produced by {offenders!r}. A reading capacity may supply facts "
            f"to a decision; it may not produce a decision's output. Give the reader "
            f"its own input DataState and let a decision capacity consume it."
        )


def register_reader(
    capacity_layer,
    *,
    name: str,
    source_datastate_iri: str,
    value_datastate_iri: str,
    value_description: str,
    prompt_iri: str,
    prompt_version: int,
    field_name: str,
    question: str,
    description: str,
    origin_party_phrase: str,
    source_identity_phrase: str,
    expected_basis: str,
    origin_party: str = ORIGIN_ASSERTED_BY_PARTY,
    value_shape: Optional[ShapeDescriptor] = None,
    extraction_schema: Optional[Mapping[str, Any]] = None,
    session: Any = None,
) -> Capacity:
    """Register one reader's DataStates and capacity. Idempotent.

    ``session`` registers into that user's **Local** metagraph; omit it to
    register Global. Local-first is the Decision Records trial — nothing
    reaches the Global catalog until the shape is proven. Remember that
    ``pipeline._view_for`` sees Global *or* Local and never both, so a
    Local trial means the whole path must be Local until the two-tier
    union view lands.
    """
    assert_not_an_outcome(capacity_layer, value_datastate_iri, session=session)
    metagraph = (
        capacity_layer.local_metagraph(session.user_id)
        if session is not None
        else capacity_layer.global_metagraph()
    )
    ds_graph = ensure_datastate_graph(metagraph, strict=capacity_layer._strict)
    for ds in reader_datastates(
        value_datastate_iri=value_datastate_iri,
        value_description=value_description,
        value_shape=value_shape,
    ):
        if datastate_iri(ds.name) not in ds_graph.nodes:
            capacity_layer.register_datastate(ds, session=session, allow_new_realm=True)
    capacity = build_reader(
        name=name,
        source_datastate_iri=source_datastate_iri,
        value_datastate_iri=value_datastate_iri,
        prompt_iri=prompt_iri,
        prompt_version=prompt_version,
        field_name=field_name,
        question=question,
        description=description,
        origin_party=origin_party,
        origin_party_phrase=origin_party_phrase,
        source_identity_phrase=source_identity_phrase,
        expected_basis=expected_basis,
        value_shape=value_shape,
        extraction_schema=extraction_schema,
    )
    if capacity.iri not in capacity_layer._capacity_index.get(metagraph.metagraph_id, {}):
        capacity_layer.register_capacity(capacity, session=session)
    return capacity


def source_text_datastate(name: str, description: str) -> DataState:
    """A document a reader reads. One per document kind, not one shared —
    two documents in a run need two types (one value per DataState IRI)."""
    return DataState(
        name=name,
        shape=ShapeDescriptor.scalar("str", opaque_tag=name),
        description=description,
        provenance_category=CATEGORY_COMPREHENSION,
    )


__all__ = [
    "ORIGIN_PARTIES",
    "READER_POSSIBLE_REFUSAL_REASONS",
    "READER_SUPPLIED_FIELDS",
    "assert_not_an_outcome",
    "build_reader",
    "coerce_to_shape",
    "locate_quote",
    "reader_datastates",
    "register_reader",
    "source_text_datastate",
]
