"""``mindsos_knowledge.policies`` — as-of selection and the guarded write.

The role shipped the shape and a docstring saying what an as-of lookup means.
Nothing implemented it, and the sentence it has to get right is *select the
edition whose window CONTAINS the date, not the latest*. Every test here is
about a way "the latest" would have been wrong.
"""

from __future__ import annotations

import pytest

from mindsos_knowledge.identifiers import ROLE_POLICIES
from mindsos_knowledge.knowledge_layer import KnowledgeLayer
from mindsos_knowledge.policies import (
    AmbiguousEditionsError,
    EditionExistsError,
    NoEditionInForceError,
    PROP_STATED_VALUE,
    edition_in_force,
    editions_of,
    write_policy_edition,
)
from mindsos_knowledge.schemas.policies import NODE_POLICY_EDITION

from ._dr_fixtures import (
    EDITION_2023,
    EDITION_2024,
    POLICY_ID,
    build_kl,
    build_kl_with_both,
)


def _view(kl):
    return kl.global_view()


def test_the_edition_in_force_is_not_the_latest_edition():
    """THE test. Ask about 2023 with a 2024 edition present.

    "The latest" answers 29,200 and is wrong for every question about the past.
    A Decision Record rendered a year after the fact resolves the edition that
    was in force when it ran, or it misstates the authority it cites.
    """
    kl = build_kl_with_both()
    edition = edition_in_force(_view(kl), policy_id=POLICY_ID, as_of="2023-06-30")
    assert (edition.properties or {})[PROP_STATED_VALUE] == 27700


def test_the_open_ended_edition_covers_any_later_date():
    kl = build_kl_with_both()
    for as_of in ("2024-01-01", "2024-04-15", "2031-12-31"):
        edition = edition_in_force(_view(kl), policy_id=POLICY_ID, as_of=as_of)
        assert (edition.properties or {})[PROP_STATED_VALUE] == 29200


def test_the_window_is_inclusive_at_both_ends():
    kl = build_kl_with_both()
    first = edition_in_force(_view(kl), policy_id=POLICY_ID, as_of="2023-01-01")
    last = edition_in_force(_view(kl), policy_id=POLICY_ID, as_of="2023-12-31")
    assert (first.properties or {})[PROP_STATED_VALUE] == 27700
    assert (last.properties or {})[PROP_STATED_VALUE] == 27700


def test_a_date_before_every_edition_refuses_rather_than_falling_back():
    kl = build_kl_with_both()
    with pytest.raises(NoEditionInForceError) as excinfo:
        edition_in_force(_view(kl), policy_id=POLICY_ID, as_of="2019-04-15")
    assert excinfo.value.considered == 2


def test_an_unknown_authority_refuses_with_nothing_considered():
    kl = build_kl_with_both()
    with pytest.raises(NoEditionInForceError) as excinfo:
        edition_in_force(_view(kl), policy_id="policy:not_ours", as_of="2024-04-15")
    assert excinfo.value.considered == 0


def test_overlapping_windows_raise_and_name_both_editions():
    """Not a refusal. There is no tie-break that would not state an authority
    the store does not actually agree on, so the caller decides."""
    kl = build_kl(
        EDITION_2023,
        dict(
            version="2023.2",
            in_force_from="2023-06-01",
            in_force_to="2023-12-31",
            stated_value=28000,
            text="An overlapping restatement.",
        ),
    )
    with pytest.raises(AmbiguousEditionsError) as excinfo:
        edition_in_force(_view(kl), policy_id=POLICY_ID, as_of="2023-07-01")
    assert excinfo.value.versions == ("2023.1", "2023.2")


def test_dates_are_parsed_not_string_compared():
    kl = build_kl_with_both()
    with pytest.raises(ValueError):
        edition_in_force(_view(kl), policy_id=POLICY_ID, as_of="15/04/2024")


def test_a_malformed_stored_window_raises_rather_than_sorting():
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, ROLE_POLICIES, "global")
    iri = handle.mint_iri(NODE_POLICY_EDITION, policy_id=POLICY_ID, edition_id="bad")
    handle.graph().add_node(
        value="",
        type_name=NODE_POLICY_EDITION,
        node_id=iri,
        properties={"policy_id": POLICY_ID, "version": "bad", "in_force_from": "soon"},
    )
    with pytest.raises(ValueError):
        edition_in_force(_view(kl), policy_id=POLICY_ID, as_of="2024-04-15")


def test_an_inverted_window_is_refused_at_write_time():
    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, ROLE_POLICIES, "global")
    with pytest.raises(ValueError):
        write_policy_edition(
            handle,
            policy_id=POLICY_ID,
            version="2024.9",
            in_force_from="2024-12-31",
            in_force_to="2024-01-01",
        )


def test_rewriting_an_edition_is_refused_at_this_door():
    """Append-only, made real where it can be.

    ``validate_mutation_discipline`` is still uncalled system-wide and
    ``tests/policy_role/test_policy_role_core.py::
    test_append_only_is_declared_but_not_enforced`` still pins that hole. This
    is the narrower claim that IS true: the one writer that populates the store
    refuses to replace an edition. Correcting an authority means appending an
    edition with its own window.
    """
    kl = build_kl(EDITION_2024)
    handle = kl.writeable(None, ROLE_POLICIES, "global")
    with pytest.raises(EditionExistsError):
        write_policy_edition(
            handle,
            policy_id=POLICY_ID,
            version="2024.1",
            in_force_from="2024-01-01",
            stated_value=99999,
            text="A silent restatement.",
        )
    assert (
        edition_in_force(_view(kl), policy_id=POLICY_ID, as_of="2024-04-15").properties
    )[PROP_STATED_VALUE] == 29200


def test_the_text_is_the_payload_and_the_operand_is_a_property():
    """``value`` is a RESERVED_PROPERTY_KEYS member owned by the Core Layer, so
    the authority's words are the node payload and the number a criterion
    compares against is ``stated_value``. Invisible until the first write, and
    this is the first write."""
    kl = build_kl(EDITION_2024)
    edition = edition_in_force(_view(kl), policy_id=POLICY_ID, as_of="2024-04-15")
    assert edition.value == EDITION_2024["text"]
    assert (edition.properties or {})[PROP_STATED_VALUE] == 29200
    assert "value" not in (edition.properties or {})


def test_editions_of_returns_every_edition_of_one_authority():
    kl = build_kl_with_both()
    assert len(editions_of(_view(kl), POLICY_ID)) == 2
    assert editions_of(_view(kl), "policy:not_ours") == []
