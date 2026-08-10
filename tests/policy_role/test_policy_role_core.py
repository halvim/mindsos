"""CORE CR: the policy role — dated, versioned editions of an authority.

Non-Falkor substrate: role closure + dual scope, schema shape, IRI
round-trip, and the two properties that make an *as-of* lookup possible at
all (an open-ended window, and selection by containment rather than by
recency).

**One test here deliberately pins a GAP rather than a guarantee** —
:func:`test_append_only_is_declared_but_not_enforced`. See its docstring.
"""

from __future__ import annotations

import pytest

from mindsos_core import Metagraph

from mindsos_knowledge import (
    ALL_ROLES,
    ROLE_POLICIES,
    parse_iri,
    policy_edition_iri,
)
from mindsos_knowledge.bootstrap import (
    _GLOBAL_NAMED_ROLES,
    _LOCAL_NAMED_ROLES,
    ensure_global_role_graph,
    ensure_local_role_graph,
)
from mindsos_knowledge.schemas import schema_for_role
from mindsos_knowledge.schemas._base import Discipline
from mindsos_knowledge.schemas.policies import (
    NODE_POLICY_EDITION,
    POLICIES_EDGE_TYPES,
    POLICIES_NODE_TYPES,
    POLICY_EDITION_PROPS,
    STORAGE_MODE_FIELDS,
    build_policies_schema,
)


POLICY_ID = "policy:filing_threshold"


# ── role closure + scope ──────────────────────────────────────────────


def test_role_is_in_closed_set_and_dual_scope() -> None:
    """17th role. The count is asserted in four other suites too — that is
    the closed-set guard, and bumping it is meant to be a deliberate act."""
    assert ROLE_POLICIES in ALL_ROLES
    assert len(ALL_ROLES) == 17
    assert ROLE_POLICIES in _GLOBAL_NAMED_ROLES
    assert ROLE_POLICIES in _LOCAL_NAMED_ROLES


def test_schema_is_single_type_zero_edge_append_only() -> None:
    s = build_policies_schema()
    assert s.mutation_discipline == Discipline.APPEND_ONLY
    assert schema_for_role(ROLE_POLICIES).mutation_discipline == (
        Discipline.APPEND_ONLY
    )
    assert POLICIES_NODE_TYPES == (NODE_POLICY_EDITION,)
    assert POLICIES_EDGE_TYPES == ()


def test_both_scopes_are_append_only() -> None:
    """Not a parity accident — a Local realm that permitted rewriting would
    let a user silently restate what a policy said. That is the capacity-level
    form of the objection that kept this store out of ``learned-parameters``,
    where Local shadows Global per knob."""
    assert build_policies_schema(scope="global").mutation_discipline == (
        Discipline.APPEND_ONLY
    )
    assert build_policies_schema(scope="local").mutation_discipline == (
        Discipline.APPEND_ONLY
    )


def test_the_payload_is_the_large_field_and_it_is_the_text() -> None:
    """An authority's TEXT is what is long; its threshold is a scalar. The
    payload key is ``value`` because that is the node payload field
    ``learned-parameters`` also declares — not a property of that name."""
    assert STORAGE_MODE_FIELDS == {NODE_POLICY_EDITION: frozenset({"value"})}


def test_the_comparison_value_is_not_called_value() -> None:
    """``value`` is in ``RESERVED_PROPERTY_KEYS`` — the Core Layer owns it as
    the node payload. A ``PolicyEdition`` declaring a ``value`` PROPERTY would
    raise ``PropertyShapeError`` at registration, so the criterion's operand is
    ``stated_value``. This test exists because the collision is invisible until
    the first write, and the first write is in another lane."""
    from mindsos_core.schema import RESERVED_PROPERTY_KEYS

    assert "value" in RESERVED_PROPERTY_KEYS
    assert "value" not in POLICY_EDITION_PROPS
    assert "stated_value" in POLICY_EDITION_PROPS


def test_props_carry_the_window_and_the_identity() -> None:
    for field in (
        "policy_id", "version", "in_force_from", "in_force_to", "stated_value"
    ):
        assert field in POLICY_EDITION_PROPS


# ── IRI round-trip ────────────────────────────────────────────────────


def test_iri_round_trips_with_colons_in_the_policy_id() -> None:
    """``policy_id`` is itself a colon-bearing IRI, so the body must stay
    opaque after the ``edition:`` kind (the PB-8 precedent)."""
    iri = policy_edition_iri("v1", POLICY_ID, "2024.1")
    assert iri == "policies-v1:edition:policy:filing_threshold:2024.1"
    parsed = parse_iri(iri)
    assert parsed.role == ROLE_POLICIES
    assert parsed.version == "v1"
    assert parsed.kind == "edition"
    assert parsed.body == "policy:filing_threshold:2024.1"
    assert parsed.full == iri


def test_two_editions_of_one_authority_are_distinct_nodes() -> None:
    """The whole point of the store: one authority, many editions, each its
    own node. If these collided, run 5 — same case at two dates — could not
    exist."""
    a = policy_edition_iri("v1", POLICY_ID, "2023.1")
    b = policy_edition_iri("v1", POLICY_ID, "2024.1")
    assert a != b


def test_mint_iri_dispatches_on_role_and_nodetype() -> None:
    from mindsos_knowledge.identifiers import _IRI_BUILDERS

    minter = _IRI_BUILDERS[(ROLE_POLICIES, NODE_POLICY_EDITION)]
    assert minter("v1", policy_id=POLICY_ID, edition_id="2024.1") == (
        policy_edition_iri("v1", POLICY_ID, "2024.1")
    )


def test_mint_iri_raises_on_a_missing_key() -> None:
    """``KeyError`` per ADR-0146 §Decision — a missing key is programmer
    error, not a runtime condition to soften."""
    from mindsos_knowledge.identifiers import _IRI_BUILDERS

    minter = _IRI_BUILDERS[(ROLE_POLICIES, NODE_POLICY_EDITION)]
    with pytest.raises(KeyError):
        minter("v1", policy_id=POLICY_ID)


# ── role graphs exist in both realms ──────────────────────────────────


def test_role_graph_is_creatable_in_both_realms() -> None:
    g_global = ensure_global_role_graph(Metagraph("kl:global"), ROLE_POLICIES)
    assert g_global.role == ROLE_POLICIES
    assert g_global.schema.mutation_discipline == Discipline.APPEND_ONLY

    g_local = ensure_local_role_graph(Metagraph("kl:local:alice"), ROLE_POLICIES)
    assert g_local.role == ROLE_POLICIES
    assert g_local.schema.mutation_discipline == Discipline.APPEND_ONLY


# ── the gap, pinned ───────────────────────────────────────────────────


def test_append_only_is_declared_but_not_enforced() -> None:
    """**This test pins a HOLE, and it should fail the day the hole closes.**

    ``validate_mutation_discipline`` is uncalled system-wide — stated outright
    in ``schemas/dataset.py`` — so ``append_only`` is a declared, forward-
    looking discipline and nothing in core stops an edition being overwritten.

    The role is worth having anyway: it declares the discipline it needs, and
    the declaration is what a later enforcement pass reads. But "append-only
    policy store" is a sentence someone will put in front of a customer, and
    it is not true of the substrate today — only of the intent. Pinning it
    here means the claim cannot quietly become folklore.

    When enforcement lands, this test goes red. Delete it then, and say so in
    the commit.
    """
    schema = build_policies_schema()
    assert schema.mutation_discipline == Discipline.APPEND_ONLY
    assert not hasattr(schema, "enforce_mutation_discipline")

    graph = ensure_global_role_graph(Metagraph("kl:global"), ROLE_POLICIES)
    iri = policy_edition_iri("v1", POLICY_ID, "2024.1")
    graph.add_node(
        value="Gross income of $29,200 or more requires a return for tax year 2024.",
        type_name=NODE_POLICY_EDITION,
        properties={
            "policy_id": POLICY_ID,
            "version": "2024.1",
            "in_force_from": "2024-01-01",
            "stated_value": 29200,
        },
        node_id=iri,
    )
    # Nothing raises: the node's properties are mutable in place, which is
    # precisely what append_only is supposed to forbid.
    graph.nodes[iri].properties["stated_value"] = 1
    assert graph.nodes[iri].properties["stated_value"] == 1
