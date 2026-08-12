"""Structured ingest v0 — read one declared field out of a structured record.

**The control arm.** ``DECISION_RECORDS_DEMO_PLAN.md`` claim 5 is *the model
reads, it does not decide*, and the way that is shown is running the same
cases twice: once with values supplied structured, once with a model reading
prose, and demonstrating **identical answers with different origins**. This is
the structured half. It exists so the model half has something to be compared
against, which is why it is not throwaway.

**Category is ``retrieval``, for the reason ADR-0208 D1 gives.** A reader that
may find nothing needs the ``OPTIONAL_RETURN`` family rule, and ``retrieval``
is the bootstrapped category that carries it. ``comprehension`` would be
actively wrong here: nothing is comprehended, there is no model, and filing it
under a reading family would make the one producer that provably does not use
a model look like the one that does.

**``origin_method`` is ``read_from_source``, and that is the point of this
module.** The stand-in reader it replaces stamped ``read_by_model`` on every
record while no model existed anywhere in the system — false provenance in the
product whose entire claim is provenance, and it appeared on three of the five
runs. Probe D found it by rendering the graph; nothing else would have.

**Two refusals, both returning, both declared on every record.**

* ``field_absent`` — the record does not carry the field. A finding about the
  material, so it returns: the value is ``None``, the origin record carries the
  reason, and a consuming criterion sees the ``None`` and declines to guess.
* ``value_not_coercible`` — the field is there and cannot be read as the
  declared shape (``"none"`` where an integer belongs). Deliberately NOT folded
  into ``field_absent``: *"they did not state it"* and *"they stated something
  that is not a number"* are different facts about the customer's material, and
  a Record that confused them would be false.

**A source that is not a record raises**, and is not a refusal at all. The
capacity was wired to something it cannot read — our defect, never a finding
about the case — so it is reported the way an outage is, by L-2's terminal
node, rather than written into a record as though the material were at fault.
Same split as ``policy_lookup_v0``'s ``source_unreachable``.

**Placement.** The factory is core (RULES §8): the next consumer of a
structured payload must not re-derive how a value and its origin reach the
grounding graph. One particular field, one vocabulary and one prose phrase are
content and belong to whoever is asking the question.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..identifiers import CATEGORY_RETRIEVAL, capacity_iri
from ..printable import PhraseNotPrintable, describes_without_naming
from .origin_v0 import (
    BASIS_STATED,
    FIELD_BASIS,
    ORIGIN_READ_FROM_SOURCE,
    ORIGIN_SHAPE_TAG,
    OriginContractError,
    PRODUCER_STRUCTURED_INGEST,
    REFUSAL_FIELD_ABSENT,
    REFUSAL_VALUE_NOT_COERCIBLE,
    assert_printable_phrase,
    build_origin_record,
    origin_record_iri,
)

#: The category every reader built here registers into.
CATEGORY = CATEGORY_RETRIEVAL

#: Everything a structured-ingest reader could ever refuse with. Declared on
#: every record, admitted or not, so a renderer can tell *"this producer could
#: never say that"* from *"this producer happened not to"*.
POSSIBLE_REFUSAL_REASONS = (REFUSAL_FIELD_ABSENT, REFUSAL_VALUE_NOT_COERCIBLE)

#: Producer-declared fields a reader populates when it admits a value.
SUPPLIED_WHEN_ADMITTED = (FIELD_BASIS,)

#: Coercions this reader will perform. Narrow **on purpose**: a reader that
#: guesses is a reader that invents provenance. ``int("61000")`` is reading;
#: parsing ``"sixty-one thousand"`` would be interpreting, which is the other
#: producer's job and carries a different ``origin_method``.
_COERCIONS = {"int": int, "float": float, "str": str, "bool": bool}


class StructuredSourceUnreadableError(RuntimeError):
    """The source was not a record this reader could read at all.

    A wiring defect on our side, never a finding about the customer's
    material — see the module docstring. ``str(exc)`` becomes L-2's
    ``stopped_detail`` and a Decision Record prints it, so the message is
    prose and carries no token; the machine-readable reason is
    :attr:`refusal_reason`.
    """

    refusal_reason = None


def structured_value_datastates(
    *,
    value_name: str,
    value_elem: str,
    value_description: str,
    origin_description: str = "",
) -> List[DataState]:
    """The two DataStates a structured-ingest reader produces.

    ``value_elem`` is a real primitive, never opaque, for the same reason the
    policy limit is: a value core cannot check must not reach a capacity that
    decides.
    """
    if value_elem not in _COERCIONS:
        raise OriginContractError(
            f"value_elem must be one of {sorted(_COERCIONS)}, got {value_elem!r}"
        )
    resolved_origin = (
        origin_description or f"where {value_description} came from"
    )
    for text, field in ((value_description, "value_description"),
                        (resolved_origin, "origin_description")):
        try:
            describes_without_naming(text, field, value_name)
        except PhraseNotPrintable as exc:
            raise OriginContractError(str(exc)) from exc
    return [
        DataState(
            name=value_name,
            shape=ShapeDescriptor.scalar(value_elem),
            description=value_description,
        ),
        DataState(
            name=f"{value_name}_origin",
            shape=ShapeDescriptor.opaque(ORIGIN_SHAPE_TAG),
            description=resolved_origin,
        ),
    ]


def build_structured_ingest_reader(
    *,
    name: str,
    field: str,
    value_datastate_iri: str,
    value_elem: str,
    source_datastate_iri: str,
    source_identity_phrase: str,
    question: str,
    printable_phrase: str = "",
    description: str = "",
) -> Capacity:
    """Build a reader of one declared field out of one structured source.

    Args:
        field: The key read out of the source record. Bound at build time,
            never taken as a runtime input — a reader whose field varied per
            run could not declare what it produces, and the grounding graph
            would record a value nothing explains.
        source_identity_phrase: Registered prose naming the source, printed by
            the Record ("their filed return"). Validated here, because
            catching an identifier at registration beats catching it in front
            of a lawyer.
    """
    assert_printable_phrase(source_identity_phrase, "source_identity_phrase")
    assert_printable_phrase(question, "question")
    printable_phrase = printable_phrase or f"reading {source_identity_phrase}"
    assert_printable_phrase(printable_phrase, "printable_phrase")
    if value_elem not in _COERCIONS:
        raise OriginContractError(
            f"value_elem must be one of {sorted(_COERCIONS)}, got {value_elem!r}"
        )
    origin_iri = origin_record_iri(value_datastate_iri)
    coerce = _COERCIONS[value_elem]

    def _refused(reason: str, detail: str) -> Dict[str, Any]:
        return {
            value_datastate_iri: None,
            origin_iri: build_origin_record(
                producer_kind=PRODUCER_STRUCTURED_INGEST,
                origin_method=ORIGIN_READ_FROM_SOURCE,
                source_identity_phrase=source_identity_phrase,
                source_datastate=source_datastate_iri,
                question=question,
                admitted=False,
                supplied_fields=(),
                possible_refusal_reasons=POSSIBLE_REFUSAL_REASONS,
                refusal_reason=reason,
                refusal_detail=detail,
            ),
        }

    def _read(context: Any = None, **inputs: Any) -> Dict[str, Any]:
        source = inputs.get(source_datastate_iri)
        if not isinstance(source, Mapping):
            raise StructuredSourceUnreadableError(
                f"{source_identity_phrase} could not be read, because what was "
                f"supplied is not a record of stated values. This is a fault "
                f"on our side and is never a finding about the case."
            )
        if field not in source or source[field] is None:
            return _refused(
                REFUSAL_FIELD_ABSENT,
                f"{source_identity_phrase} does not state it.",
            )
        raw = source[field]
        try:
            value = coerce(raw)
        except (TypeError, ValueError):
            return _refused(
                REFUSAL_VALUE_NOT_COERCIBLE,
                f"{source_identity_phrase} states something that could not be "
                f"read as a number.",
            )
        return {
            value_datastate_iri: value,
            origin_iri: build_origin_record(
                producer_kind=PRODUCER_STRUCTURED_INGEST,
                origin_method=ORIGIN_READ_FROM_SOURCE,
                source_identity_phrase=source_identity_phrase,
                source_datastate=source_datastate_iri,
                question=question,
                admitted=True,
                supplied_fields=SUPPLIED_WHEN_ADMITTED,
                possible_refusal_reasons=POSSIBLE_REFUSAL_REASONS,
                **{FIELD_BASIS: BASIS_STATED},
            ),
        }

    return Capacity(
        name=name,
        category=CATEGORY,
        inputs=(source_datastate_iri,),
        outputs=(value_datastate_iri, origin_iri),
        description=description or f"reads one stated value from {source_identity_phrase}",
        printable_phrase=printable_phrase,
        implementation=_read,
    )


def structured_reader_iri(name: str) -> str:
    """The capacity IRI a reader named ``name`` registers at."""
    return capacity_iri(CATEGORY, name)


__all__ = [
    "CATEGORY",
    "POSSIBLE_REFUSAL_REASONS",
    "SUPPLIED_WHEN_ADMITTED",
    "StructuredSourceUnreadableError",
    "build_structured_ingest_reader",
    "structured_reader_iri",
    "structured_value_datastates",
]
