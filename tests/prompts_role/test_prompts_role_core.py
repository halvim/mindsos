"""The prompts role — versioned prompt text (``mindsos_llm`` plan item I-9).

Non-Falkor substrate: role closure + dual scope, schema shape, IRI
round-trip, the append-only refusal, and the one conversion this role lives
or dies by — ``prompt_version`` is an ``int`` on every answer and a string
inside an IRI.

**Two tests here pin a GAP rather than a guarantee** —
:func:`test_append_only_is_declared_but_not_enforced` and
:func:`test_a_missing_edition_refuses_rather_than_returning_a_neighbour`.
Both say so in their own docstrings.
"""

from __future__ import annotations

import pytest

from mindsos_core import Metagraph

from mindsos_knowledge import (
    ALL_ROLES,
    ROLE_PROMPTS,
    parse_iri,
    prompt_edition_iri,
)
from mindsos_knowledge.bootstrap import (
    _GLOBAL_NAMED_ROLES,
    _LOCAL_NAMED_ROLES,
    ensure_global_role_graph,
    ensure_local_role_graph,
)
from mindsos_knowledge.prompts import (
    PROP_PROMPT_IRI,
    PROP_PROMPT_VERSION,
    PromptEditionNotFoundError,
    edition_id_for,
)
from mindsos_knowledge.schemas import schema_for_role
from mindsos_knowledge.schemas._base import Discipline
from mindsos_knowledge.schemas.prompts import (
    NODE_PROMPT_EDITION,
    PROMPTS_EDGE_TYPES,
    PROMPTS_NODE_TYPES,
    PROMPT_EDITION_PROPS,
    STORAGE_MODE_FIELDS,
    build_prompts_schema,
)


PROMPT_IRI = "prompt:extract_purchase_date"


# ── role closure + scope ──────────────────────────────────────────────


def test_role_is_in_closed_set_and_dual_scope() -> None:
    """18th role. The count is asserted in five other suites and derived by
    the doc guard — bumping it is meant to be a deliberate act."""
    assert ROLE_PROMPTS in ALL_ROLES
    assert len(ALL_ROLES) == 18
    assert ROLE_PROMPTS in _GLOBAL_NAMED_ROLES
    assert ROLE_PROMPTS in _LOCAL_NAMED_ROLES


def test_schema_is_single_type_zero_edge_append_only() -> None:
    s = build_prompts_schema()
    assert s.mutation_discipline == Discipline.APPEND_ONLY
    assert schema_for_role(ROLE_PROMPTS).mutation_discipline == (
        Discipline.APPEND_ONLY
    )
    assert PROMPTS_NODE_TYPES == (NODE_PROMPT_EDITION,)
    assert PROMPTS_EDGE_TYPES == ()


def test_both_scopes_are_append_only() -> None:
    """Not a parity accident. A Local realm that permitted rewriting would let
    a user silently restate what was asked, and *shown* would stop meaning
    *what ran* — which is the only reason this role exists."""
    for scope in ("global", "local"):
        assert build_prompts_schema(scope=scope).mutation_discipline == (
            Discipline.APPEND_ONLY
        )


def test_the_payload_is_the_large_field_and_it_is_the_text() -> None:
    """``value`` is the node payload (``RESERVED_PROPERTY_KEYS``), so the text
    is not a property and ``text`` is not a property name."""
    assert STORAGE_MODE_FIELDS[NODE_PROMPT_EDITION] == frozenset({"value"})
    assert "text" not in PROMPT_EDITION_PROPS
    assert "value" not in PROMPT_EDITION_PROPS
    assert PROP_PROMPT_IRI in PROMPT_EDITION_PROPS
    assert PROP_PROMPT_VERSION in PROMPT_EDITION_PROPS


def test_role_graph_is_creatable_in_both_realms() -> None:
    g_global = ensure_global_role_graph(Metagraph("kl:global"), ROLE_PROMPTS)
    assert g_global.role == ROLE_PROMPTS
    g_local = ensure_local_role_graph(Metagraph("kl:local:alice"), ROLE_PROMPTS)
    assert g_local.role == ROLE_PROMPTS


# ── the address a stored conclusion can resolve ───────────────────────


def test_iri_round_trips_with_colons_in_the_prompt_iri() -> None:
    """``prompt_iri`` normally carries a colon — it is an IRI. The body stays
    opaque after the ``edition:`` kind, as for ``policy_edition_iri`` and
    ``learned_pipeline_iri`` (PB-8 precedent)."""
    iri = prompt_edition_iri("v1", PROMPT_IRI, "3")
    assert iri == f"prompts-v1:edition:{PROMPT_IRI}:3"
    parsed = parse_iri(iri)
    assert parsed.role == ROLE_PROMPTS
    assert parsed.version == "v1"
    assert parsed.kind == "edition"
    assert parsed.body == f"{PROMPT_IRI}:3"
    assert parsed.full == iri


def test_mint_iri_dispatches_on_role_and_nodetype() -> None:
    from mindsos_knowledge.identifiers import _IRI_BUILDERS

    minter = _IRI_BUILDERS[(ROLE_PROMPTS, NODE_PROMPT_EDITION)]
    assert minter("v1", prompt_iri=PROMPT_IRI, prompt_version="3") == (
        prompt_edition_iri("v1", PROMPT_IRI, "3")
    )


def test_mint_iri_raises_on_a_missing_key() -> None:
    """``KeyError`` per ADR-0146 §Decision — a missing key is programmer
    error, not a runtime condition to soften."""
    from mindsos_knowledge.identifiers import _IRI_BUILDERS

    minter = _IRI_BUILDERS[(ROLE_PROMPTS, NODE_PROMPT_EDITION)]
    with pytest.raises(KeyError):
        minter("v1", prompt_iri=PROMPT_IRI)


# ── the one int -> str crossing ───────────────────────────────────────


def test_the_version_conversion_has_exactly_one_spelling() -> None:
    """⚠ THE DEFECT THIS ROLE IS MOST EXPOSED TO. ``prompt_version`` is an
    ``int`` on every answer and a string inside an IRI. If the writer and the
    reader each spell that crossing themselves, a write of ``3`` and a read of
    ``"3"`` miss — and the miss reads as *"the prompt was never stored"*
    rather than as *"you asked in a different alphabet"*.

    ``edition_id_for`` is the only crossing, so int and str address the same
    node by construction."""
    assert edition_id_for(3) == edition_id_for("3") == "3"
    assert prompt_edition_iri("v1", PROMPT_IRI, edition_id_for(3)) == (
        prompt_edition_iri("v1", PROMPT_IRI, edition_id_for("3"))
    )


def test_a_missing_edition_refuses_rather_than_returning_a_neighbour() -> None:
    """⚠ A GAP PINNED AS BEHAVIOUR. Every conclusion written before this role
    existed names a version that was never stored. The store says so; it does
    not fall back to the nearest version, because a reader shown a prompt that
    was not the one that ran has been told something false — which is worse
    than being told the text is absent.

    Exercised against a fabricated view, so it needs no store and cannot pass
    for an unrelated reason."""
    from mindsos_knowledge.prompts import edition_at_version, prompt_text

    class _EmptyView:
        def iter_nodes(self, role, type_=None):
            return iter(())

    for call in (edition_at_version, prompt_text):
        with pytest.raises(PromptEditionNotFoundError):
            call(_EmptyView(), prompt_iri=PROMPT_IRI, prompt_version=3)


def test_append_only_is_declared_but_not_enforced() -> None:
    """⚠ A GAP PINNED AS A TEST, not a guarantee. The schema declares
    ``append_only`` and ``validate_mutation_discipline`` is uncalled
    system-wide, so nothing in the substrate stops an edition being
    overwritten; :func:`~mindsos_knowledge.prompts.write_prompt_edition`
    refuses a duplicate, and that refusal is the only enforcement there is.

    Consequence, and it is the module's own honesty problem: *shown* means
    RETRIEVABLE, not VERIFIABLE. Filed as
    ``core-llm-prompt-edition-append-only-unenforced``. This test exists so
    the day the substrate enforces it, this line fails and someone reads the
    sentence above."""
    schema = build_prompts_schema()
    assert schema.mutation_discipline == Discipline.APPEND_ONLY
    assert not hasattr(schema, "enforced_mutation_discipline")
