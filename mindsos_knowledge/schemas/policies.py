"""Policies role-graph schema (CORE CR: the policy role — NET-NEW).

Per ADR-0150 §amendment-<N> (number unassigned). Dual-scope (Global + Local)
with **one** discipline on both: ``append_only``. An authority's editions are
never rewritten — see :func:`~mindsos_knowledge.identifiers.policy_edition_iri`
for why, and read the enforcement caveat at the bottom of this docstring
before relying on the word.

Single NodeType (``PolicyEdition``); no EdgeTypes in v1 — mirrors the
``learned-parameters`` / ``learned-pipelines`` zero-edge shape. Ordering
between editions is **derived from the in-force window**, not stored as an
edge or an ordinal: two editions of one authority are related by their dates
and by nothing else, and an edge would be a second place for that truth to
live (ADR-0192's criterion, the same one that rejected a stored ``fundamental``
boolean and a stored step order).

**Why the shape is core's and not the owner's.** ``dataset:<name>`` schemas are
registered per instance because shapes genuinely differ per brain (ADR-0150
§am-9: "core owns no dataset shape"). The opposite holds here: ``in_force_from``
/ ``in_force_to`` / version / text is the *same* shape for a statutory dollar
threshold and for a versioned prompt body, and that generality is the entire
argument for the role existing. A per-owner shape registry would hand back the
doctrine the role was created to buy.

**The node's ``value`` payload IS the edition's text.** Not a property —
``value`` is a ``RESERVED_PROPERTY_KEYS`` member (``mindsos_core`` owns it as
the node payload), so a ``text`` property would be the only place to put long
prose and property bags are primitives-only and always inline.
``learned-parameters`` sets the precedent: ``learn_parameter`` calls
``add_node(value=value, ...)`` and never puts ``value`` in ``props``. So here
the payload is the authority's words, and the typed thing a criterion compares
against is the ``stated_value`` **property** — deliberately not named ``value``,
which would not have been registrable.

**Per-NodeType storage_mode** (ADR-0151): the payload is the large-payload
field, exactly as ``LearnedParameter.value`` is. An authority's text is the
thing that is long; its threshold is a scalar.

``strict=False`` per ADR-0149.

⚠ **``append_only`` is DECLARED, NOT ENFORCED at v1.**
``validate_mutation_discipline`` is uncalled system-wide (stated outright in
``schemas/dataset.py``), so nothing in core stops an edition being overwritten.
This role declares the discipline it needs; the write path must enforce it.
Anyone about to write or say "append-only policy store" should read this
sentence first — the guarantee is not currently in the substrate.
"""

from __future__ import annotations

from typing import Literal

from mindsos_core import NodeType

from ._base import Discipline, L2Schema


# ── Node type ──────────────────────────────────────────────────────────

NODE_POLICY_EDITION = "PolicyEdition"

POLICIES_NODE_TYPES: tuple[str, ...] = (NODE_POLICY_EDITION,)


# ── Edge types ─────────────────────────────────────────────────────────

POLICIES_EDGE_TYPES: tuple[str, ...] = ()  # v1 has no edge types.


# ── Advisory property constants ────────────────────────────────────────

POLICY_EDITION_PROPS: frozenset[str] = frozenset({
    # Identity of the authority, and of this edition within it.
    "policy_id",
    "version",
    # The in-force window. ``in_force_to`` absent or None = open-ended, i.e.
    # this is the edition still in force. As-of lookup selects the edition
    # whose window CONTAINS the asked-about date — NOT the latest edition,
    # which is a different and wrong answer for any question about the past.
    "in_force_from",
    "in_force_to",
    # The typed thing a criterion compares against, when the edition has one
    # (a dollar threshold, a day count). Absent for an edition that is prose
    # only — a versioned prompt body has no such value. NOT named ``value``:
    # that key is reserved by the Core Layer and would raise at registration.
    "stated_value",
    "storage_mode",
    "recorded_at",
})

#: The edition's authoritative text is the node's ``value`` **payload**, not a
#: property — see the module docstring. Named here so a reader looking for
#: "where does the text live" finds the answer next to the property list.
PAYLOAD_IS_EDITION_TEXT = True


# ── Per-NodeType large-payload field declaration (ADR-0151) ───────────
#
# ``value`` is the node payload field (the edition text), matching the key
# ``learned-parameters`` declares for ``LearnedParameter.value``.

STORAGE_MODE_FIELDS: dict[str, frozenset[str]] = {
    NODE_POLICY_EDITION: frozenset({"value"}),
}


def build_policies_schema(
    strict: bool = False,
    scope: Literal["local", "global"] = "global",
) -> L2Schema:
    """Construct the policies role Schema.

    ``scope`` is accepted for signature parity with the other dual-scope role
    builders and is deliberately **not** branched on: both realms are
    ``append_only``. An authority's edition history is the same kind of thing
    whoever holds it, and a Local realm that permitted rewriting would let a
    user silently restate what a policy said — the capacity-level form of the
    objection that kept this store out of ``learned-parameters`` (where Local
    shadows Global per knob).

    Args:
        strict: Opt-in property-type enforcement. Default ``False`` per
            ADR-0149.
        scope: ``"global"`` (default) or ``"local"``. Present for parity;
            both yield ``append_only``.
    """
    s = L2Schema(mutation_discipline=Discipline.APPEND_ONLY, strict=strict)

    for nt in POLICIES_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # No EdgeTypes in v1 — edition ordering is derived from the in-force
    # window, never stored.
    return s


__all__ = [
    "NODE_POLICY_EDITION",
    "PAYLOAD_IS_EDITION_TEXT",
    "POLICIES_EDGE_TYPES",
    "POLICIES_NODE_TYPES",
    "POLICY_EDITION_PROPS",
    "STORAGE_MODE_FIELDS",
    "build_policies_schema",
]
