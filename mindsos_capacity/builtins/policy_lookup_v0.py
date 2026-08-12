"""Policy-limit lookup v0 — read a stored authority as of a date.

The first reader of the ``policies`` L2 role. Produces two DataStates: the
limit the edition states, and that limit's **origin record** (``origin_v0``,
ADR-0207). Both are declared outputs, so both reach the grounding graph through
``CapacityMMWriter.record``, which writes only ``(capacity_iri, input IRIs,
outputs)`` — a value read inside a body and never declared is invisible to a
Decision Record, and that is the whole reason a lookup capacity exists rather
than a context snapshot.

**Category is ``retrieval``, not ``decision``.** An earlier ruling put the
lookup at ``capacity:decision:*`` on the grounds that it was the only IRI shape
where two rules agreed — ``family_rule_for`` returning VERDICT via the category,
and ``origin_v0.DECISION_SHAPED_CATEGORIES`` being able to see it. Neither half
holds. ``family_rule_for`` has no caller in any shipped module, so what it
returns for this IRI is a fact about nothing; and ``DECISION_SHAPED_CATEGORIES``
exists to catch an **opaque value consumed by a capacity that compares it**,
which is the criterion capacity, not this one. What is left is a lookup filed in
the decision category graph and inheriting the VERDICT don't-know contract.
``retrieval`` is one of the thirteen bootstrapped ``FUNCTIONAL_CATEGORIES`` and
its family rule is ``OPTIONAL_RETURN`` — which is what a lookup that may find
nothing actually needs.

**The authority is bound at build time; the date is an input.** A lookup is *of*
a particular authority: its registered prose phrase, its capacity IRI and its
output DataState are all specific to one. Taking the authority as a runtime
input would let the prose and the identity disagree, with the Record printing
the prose. The as-of date is the opposite — it is the question being asked, it
varies per run, and it must enter as its own DataState or the same document
asked about two dates silently becomes two documents.

**Two failures, two mechanisms, and the split is deliberate.**

* ``no_source_in_force`` — the store holds no edition covering the date. That is
  a finding about the customer's own policy set, so it **returns**: the limit is
  ``None`` and the origin record carries the reason. The criterion capacity sees
  the ``None`` and returns a not-determined verdict, and the whole run stays
  renderable.
* ``source_unreachable`` — the store could not be read at all. That is our
  outage, never a finding about their case, so it **raises**. The step fails and
  L-2's ``RunStopped`` node records it. A Record that reported an outage as a
  gap in a customer's policy set would be false.

Overlapping in-force windows raise for a third reason: the store contradicts
itself and there is no tie-break that would not state an authority the store
does not carry. ``AmbiguousEditionsError`` is deliberately not mapped to
``no_source_in_force``, which means *there is no edition*.

**Placement.** ``builtins/`` is the home for opt-in families core does not
bootstrap (``reduction_v0``, ``origin_v0``). Nothing here is bootstrapped and
nothing enters a catalog unless a caller registers it. What ships here is the
*mechanism* — read an authority as of a date and record where the value came
from — which is core by RULES §8 because the next consumer of the store must not
re-derive it. A particular limit, a particular criterion and a particular prose
phrase are content and belong to whoever is asking the question.

``mindsos_knowledge`` is imported **inside the body**, matching
``learn_parameter``: L3 declares no compile-time dependency on L2 (Phase 28
import isolation), and the selection rule stays in one place beside the role it
reads.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..identifiers import CATEGORY_RETRIEVAL, capacity_iri
from .origin_v0 import (
    FIELD_SOURCE_IN_FORCE_FROM,
    FIELD_SOURCE_IN_FORCE_TO,
    FIELD_SOURCE_VERSION,
    ORIGIN_READ_FROM_SOURCE,
    PRODUCER_POLICY_LOOKUP,
    REFUSAL_NO_SOURCE_IN_FORCE,
    REFUSAL_SOURCE_UNREACHABLE,
    assert_printable_phrase,
    build_origin_record,
    origin_record_iri,
)

#: The category every lookup built here registers into.
CATEGORY = CATEGORY_RETRIEVAL

#: Opaque tag for an origin-record DataState. Opaque is correct and is not a
#: shortcut: the union is closed by agreement and deliberately not frozen
#: (``origin_v0``), so a record shape pinned today would pin a guess. It is safe
#: here for the reason ``DECISION_SHAPED_CATEGORIES`` exists — an origin record
#: is never consumed by a capacity that compares it against a limit. The
#: **limit** carries a real shape; that one is never opaque.
ORIGIN_SHAPE_TAG = "origin.record.v0"

#: Everything a policy lookup could ever refuse with. Declared on every record,
#: admitted or not, so a renderer can tell "this producer could never say that"
#: from "this producer happened not to".
POSSIBLE_REFUSAL_REASONS = (
    REFUSAL_NO_SOURCE_IN_FORCE,
    REFUSAL_SOURCE_UNREACHABLE,
)

#: Producer-declared fields a lookup populates **when it admits a value**. On a
#: refusal nothing was obtained, so the record declares an empty set rather than
#: promising a version it does not have — inside ``supplied_fields`` a missing
#: value is a defect, and a refused lookup is not a defect.
SUPPLIED_WHEN_ADMITTED = (
    FIELD_SOURCE_VERSION,
    FIELD_SOURCE_IN_FORCE_FROM,
)


class PolicyStoreUnreachableError(RuntimeError):
    """The policy store could not be read. An environment fault, never a
    finding about the customer's case — see the module docstring."""


def policy_limit_datastates(
    *,
    limit_name: str,
    limit_elem: str,
    limit_description: str,
    origin_description: str = "",
) -> List[DataState]:
    """The two DataStates a policy-limit lookup produces.

    ``limit_name`` is a bare DataState name (``dr.filing_threshold``), not an
    IRI. ``limit_elem`` is a real primitive — ``"int"`` for a dollar threshold,
    ``"float"`` for a rate. Never opaque: a limit is the operand of a
    comparison, and a value core cannot check must not reach a capacity that
    decides.
    """
    limit = DataState(
        name=limit_name,
        shape=ShapeDescriptor.scalar(limit_elem),
        description=limit_description,
    )
    origin = DataState(
        name=f"{limit_name}_origin",
        shape=ShapeDescriptor.opaque(ORIGIN_SHAPE_TAG),
        description=(
            origin_description
            or f"where the value of {limit_name} came from, and as of when"
        ),
    )
    return [limit, origin]


def build_policy_limit_lookup(
    *,
    name: str,
    policy_id: str,
    source_identity_phrase: str,
    question: str,
    limit_datastate_iri: str,
    as_of_datastate_iri: str,
    description: str = "",
) -> Capacity:
    """Build a lookup of one authority's stated limit, as of a date.

    Args:
        name: Capacity name within :data:`CATEGORY` — the IRI is
            ``capacity:retrieval:<name>``.
        policy_id: The authority's identifier in the ``policies`` role. Bound
            here, never taken as an input.
        source_identity_phrase: Registered prose naming the authority, printed
            by the Record ("the filing-threshold policy"). Validated at build
            time — a Decision Record forbids every identifier, and catching that
            here beats catching it in front of a lawyer.
        question: Prose stating what is being asked, with a single ``{as_of}``
            placeholder for the date.
        limit_datastate_iri: Full IRI of the limit this lookup produces. Its
            origin record's IRI is derived, never passed.
        as_of_datastate_iri: Full IRI of the date DataState this lookup
            consumes.
    """
    assert_printable_phrase(source_identity_phrase, "source_identity_phrase")
    assert_printable_phrase(question, "question")
    origin_iri = origin_record_iri(limit_datastate_iri)

    def _lookup(context: Any = None, **inputs: Any) -> Dict[str, Any]:
        from mindsos_knowledge.policies import (  # local: L3 declares no L2 dep
            AmbiguousEditionsError,
            NoEditionInForceError,
            PROP_IN_FORCE_FROM,
            PROP_IN_FORCE_TO,
            PROP_STATED_VALUE,
            PROP_VERSION,
            edition_in_force,
        )

        as_of = inputs.get(as_of_datastate_iri)
        asked = question.format(as_of=as_of)

        kl = getattr(context, "kl", None)
        if kl is None:
            raise PolicyStoreUnreachableError(
                f"{REFUSAL_SOURCE_UNREACHABLE}: no knowledge layer is bound to "
                f"this invocation, so {source_identity_phrase} could not be "
                f"consulted. This is an environment fault and must never be "
                f"rendered as a finding about the case."
            )
        try:
            view = kl.global_view()
        except Exception as exc:  # noqa: BLE001 — any read failure is an outage
            raise PolicyStoreUnreachableError(
                f"{REFUSAL_SOURCE_UNREACHABLE}: {source_identity_phrase} could "
                f"not be consulted ({exc})."
            ) from exc

        try:
            edition = edition_in_force(view, policy_id=policy_id, as_of=as_of)
        except NoEditionInForceError:
            return {
                limit_datastate_iri: None,
                origin_iri: build_origin_record(
                    producer_kind=PRODUCER_POLICY_LOOKUP,
                    origin_method=ORIGIN_READ_FROM_SOURCE,
                    source_identity_phrase=source_identity_phrase,
                    source_datastate=None,
                    question=asked,
                    admitted=False,
                    supplied_fields=(),
                    possible_refusal_reasons=POSSIBLE_REFUSAL_REASONS,
                    refusal_reason=REFUSAL_NO_SOURCE_IN_FORCE,
                    refusal_detail=(
                        f"{source_identity_phrase} has no edition covering "
                        f"{as_of}."
                    ),
                ),
            }
        except AmbiguousEditionsError:
            raise
        except ValueError as exc:
            raise PolicyStoreUnreachableError(
                f"{REFUSAL_SOURCE_UNREACHABLE}: {source_identity_phrase} holds "
                f"an edition whose in-force window cannot be read ({exc})."
            ) from exc

        props = edition.properties or {}
        producer_fields: Dict[str, Any] = {
            FIELD_SOURCE_VERSION: props.get(PROP_VERSION),
            FIELD_SOURCE_IN_FORCE_FROM: props.get(PROP_IN_FORCE_FROM),
        }
        in_force_to: Optional[Any] = props.get(PROP_IN_FORCE_TO)
        if in_force_to not in (None, ""):
            producer_fields[FIELD_SOURCE_IN_FORCE_TO] = in_force_to

        return {
            limit_datastate_iri: props.get(PROP_STATED_VALUE),
            origin_iri: build_origin_record(
                producer_kind=PRODUCER_POLICY_LOOKUP,
                origin_method=ORIGIN_READ_FROM_SOURCE,
                source_identity_phrase=source_identity_phrase,
                source_datastate=None,
                question=asked,
                admitted=True,
                supplied_fields=SUPPLIED_WHEN_ADMITTED,
                possible_refusal_reasons=POSSIBLE_REFUSAL_REASONS,
                **producer_fields,
            ),
        }

    return Capacity(
        name=name,
        category=CATEGORY,
        inputs=(as_of_datastate_iri,),
        outputs=(limit_datastate_iri, origin_iri),
        description=description or f"consults {source_identity_phrase}",
        implementation=_lookup,
    )


def policy_lookup_iri(name: str) -> str:
    """The capacity IRI a lookup named ``name`` registers at."""
    return capacity_iri(CATEGORY, name)


__all__ = [
    "CATEGORY",
    "ORIGIN_SHAPE_TAG",
    "POSSIBLE_REFUSAL_REASONS",
    "PolicyStoreUnreachableError",
    "SUPPLIED_WHEN_ADMITTED",
    "build_policy_limit_lookup",
    "policy_limit_datastates",
    "policy_lookup_iri",
]
