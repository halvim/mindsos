"""As-of selection and guarded writes for the ``policies`` role.

The role itself (CORE CR: the policy role, `schemas/policies.py`) ships the
shape and says what an as-of lookup *means* — *"select the edition whose window
CONTAINS the asked-about date, NOT the latest edition, which is a different and
wrong answer for any question about the past."* Nothing implemented it. This
module does, and it lives here rather than inside the capacity that reads it
because window containment over a role-graph is a **core mechanism**: the next
consumer of the store must not re-derive it (RULES §8).

**Dates are ISO ``YYYY-MM-DD`` and are parsed, never compared as strings.** A
malformed date raises rather than sorting lexically into a plausible-looking
answer.

**The window is inclusive at both ends.** ``in_force_to`` absent or ``None``
means open-ended — the edition still in force.

**Two editions covering one date is an error, not a preference.** There is no
tie-break rule that could be right: picking the newer states an authority the
customer's own store does not agree on. :class:`AmbiguousEditionsError` names
both, and the caller decides. Deliberately NOT mapped to the
``no_source_in_force`` refusal — that reason means *there is no edition*, and a
Decision Record that said so here would be false.

**Append-only, at this door.** ``validate_mutation_discipline`` is still uncalled
system-wide, so the role's declared ``append_only`` remains unenforced in
general — ``tests/policy_role/test_policy_role_core.py::
test_append_only_is_declared_but_not_enforced`` pins that hole and stays. What
:func:`write_policy_edition` adds is narrower and real: **this** writer refuses
to replace an edition that already exists, so the one path that populates the
store cannot rewrite history. ``handle.graph().remove_node()`` still can (it is
what ``learn_parameter`` deliberately does for its overwrite-in-place knobs);
this module never does.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Iterator, List, Optional, Tuple

from .identifiers import ROLE_POLICIES
from .schemas.policies import NODE_POLICY_EDITION

# Property keys read here. They are the advisory constants declared beside the
# schema (``POLICY_EDITION_PROPS``); named again as module constants so a reader
# of the selection code can see exactly which four fields it depends on.
PROP_POLICY_ID = "policy_id"
PROP_VERSION = "version"
PROP_IN_FORCE_FROM = "in_force_from"
PROP_IN_FORCE_TO = "in_force_to"
PROP_STATED_VALUE = "stated_value"


class PolicyStoreError(Exception):
    """Base for every failure reading or writing the ``policies`` role."""


class NoEditionInForceError(PolicyStoreError):
    """No edition of ``policy_id`` has a window containing ``as_of``.

    A finding about the customer's own policy set, not an environment fault —
    the caller maps it to ``origin_v0.REFUSAL_NO_SOURCE_IN_FORCE``.
    """

    def __init__(self, policy_id: str, as_of: str, considered: int) -> None:
        self.policy_id = policy_id
        self.as_of = as_of
        self.considered = considered
        super().__init__(
            f"no edition of {policy_id!r} is in force on {as_of} "
            f"({considered} edition(s) of that authority were considered)"
        )


class AmbiguousEditionsError(PolicyStoreError):
    """More than one edition of ``policy_id`` covers ``as_of``.

    Not a refusal reason: the store contradicts itself, and every tie-break
    would state an authority the store does not actually carry.
    """

    def __init__(self, policy_id: str, as_of: str, versions: Tuple[str, ...]) -> None:
        self.policy_id = policy_id
        self.as_of = as_of
        self.versions = versions
        super().__init__(
            f"{len(versions)} editions of {policy_id!r} cover {as_of}: "
            f"{list(versions)!r}. Overlapping in-force windows are a defect in "
            f"the store; there is no correct tie-break."
        )


class EditionExistsError(PolicyStoreError):
    """An edition already exists at this ``(policy_id, version)``.

    The role is ``append_only``: an edition is never rewritten, because a
    Decision Record rendered a year later must still resolve the edition that
    was in force when it ran.
    """


def _parse(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be an ISO date string, got {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{field} must be an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


def _covers(node: Any, when: date) -> bool:
    props = node.properties or {}
    start = _parse(props.get(PROP_IN_FORCE_FROM), PROP_IN_FORCE_FROM)
    end_raw = props.get(PROP_IN_FORCE_TO)
    if end_raw in (None, ""):
        return start <= when
    return start <= when <= _parse(end_raw, PROP_IN_FORCE_TO)


def editions_of(view: Any, policy_id: str) -> List[Any]:
    """Every ``PolicyEdition`` node of ``policy_id`` in ``view``.

    ``view`` is a :class:`~mindsos_knowledge.metagraph_view.MetagraphView` —
    Global for a shared authority, Local for a user-held one. Unordered: edition
    order is derived from the windows and is never stored, so there is nothing
    here to sort by that would not be inventing an ordering.
    """
    return [
        node
        for node in view.iter_nodes(ROLE_POLICIES, type_=NODE_POLICY_EDITION)
        if (node.properties or {}).get(PROP_POLICY_ID) == policy_id
    ]


def edition_in_force(view: Any, *, policy_id: str, as_of: str) -> Any:
    """The one edition of ``policy_id`` whose window contains ``as_of``.

    Raises:
        ValueError: ``as_of`` or a stored window bound is not an ISO date.
        NoEditionInForceError: no edition covers the date.
        AmbiguousEditionsError: more than one does.
    """
    when = _parse(as_of, "as_of")
    candidates = editions_of(view, policy_id)
    covering = [node for node in candidates if _covers(node, when)]
    if not covering:
        raise NoEditionInForceError(policy_id, str(when), len(candidates))
    if len(covering) > 1:
        raise AmbiguousEditionsError(
            policy_id,
            str(when),
            tuple(
                str((n.properties or {}).get(PROP_VERSION)) for n in sorted(
                    covering, key=lambda n: str((n.properties or {}).get(PROP_VERSION))
                )
            ),
        )
    return covering[0]


def write_policy_edition(
    handle: Any,
    *,
    policy_id: str,
    version: str,
    in_force_from: str,
    in_force_to: Optional[str] = None,
    stated_value: Any = None,
    text: str = "",
    recorded_at: Optional[str] = None,
) -> Any:
    """Append one edition of ``policy_id`` through ``handle``.

    ``handle`` is a :class:`~mindsos_knowledge.write_handle.KLWriteHandle` bound
    to ``(ROLE_POLICIES, scope)``.

    ``text`` becomes the node's **payload**, because ``value`` is a
    ``RESERVED_PROPERTY_KEYS`` member owned by the Core Layer — the typed thing a
    criterion compares against is the ``stated_value`` **property**. That split
    is the role's, not this function's; it is restated here because getting it
    wrong is invisible until the first write, and this is the first write.

    ``version`` is both the edition's ``version`` property and its
    ``edition_id`` IRI fragment. One concept, one argument: two names for the
    same string is a second place for that truth to live.

    Raises:
        EditionExistsError: ``(policy_id, version)`` is already in the store.
        ValueError: a window bound is not an ISO date, or the window is
            inverted.
    """
    start = _parse(in_force_from, PROP_IN_FORCE_FROM)
    if in_force_to not in (None, ""):
        end = _parse(in_force_to, PROP_IN_FORCE_TO)
        if end < start:
            raise ValueError(
                f"in_force_to {in_force_to} precedes in_force_from "
                f"{in_force_from} for {policy_id!r} {version!r}"
            )

    iri = handle.mint_iri(
        NODE_POLICY_EDITION, policy_id=policy_id, edition_id=version
    )
    if handle.graph().nodes.get(iri) is not None:
        raise EditionExistsError(
            f"edition {version!r} of {policy_id!r} already exists at {iri}. The "
            f"policies role is append_only: correct an authority by appending a "
            f"new edition with its own in-force window, never by rewriting one."
        )

    properties = {
        PROP_POLICY_ID: policy_id,
        PROP_VERSION: version,
        PROP_IN_FORCE_FROM: str(start),
    }
    if in_force_to not in (None, ""):
        properties[PROP_IN_FORCE_TO] = str(_parse(in_force_to, PROP_IN_FORCE_TO))
    if stated_value is not None:
        properties[PROP_STATED_VALUE] = stated_value
    if recorded_at is not None:
        properties["recorded_at"] = recorded_at

    return handle.write_and_validate(
        value=text,
        type_=NODE_POLICY_EDITION,
        properties=properties,
        policy_id=policy_id,
        edition_id=version,
    )


__all__ = [
    "AmbiguousEditionsError",
    "EditionExistsError",
    "NoEditionInForceError",
    "PROP_IN_FORCE_FROM",
    "PROP_IN_FORCE_TO",
    "PROP_POLICY_ID",
    "PROP_STATED_VALUE",
    "PROP_VERSION",
    "PolicyStoreError",
    "edition_in_force",
    "editions_of",
    "write_policy_edition",
]
