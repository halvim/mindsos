"""Tests for identifier helpers and vocabulary constants.

Phase 27 port from parent ``tests_l3/unit/test_identifiers.py``.
Verbatim content; only the file location changes.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    FUNCTIONAL_CATEGORIES,
    GLOBAL_FALKOR_GRAPH,
    LOCAL_FALKOR_GRAPH_FMT,
    ROLE_DATASTATES,
    capacity_iri,
    category_role,
    datastate_iri,
    falkor_graph_name,
    parse_capacity_iri,
    parse_datastate_iri,
    slugify_user_id,
)


def test_category_role_round_trip():
    assert category_role("perception") == "capacity:perception"
    # Idempotent on already-prefixed input.
    assert category_role("capacity:perception") == "capacity:perception"


def test_role_datastates_is_stable():
    assert ROLE_DATASTATES == "capacity:datastates"
    # category_role("datastates") happens to collide with ROLE_DATASTATES.
    # Callers should use ROLE_DATASTATES directly for the shared graph.
    assert category_role("datastates") == ROLE_DATASTATES


def test_capacity_iri_shape():
    iri = capacity_iri("perception", "text.space_split")
    assert iri == "capacity:perception:text.space_split"
    assert parse_capacity_iri(iri) == ("perception", "text.space_split")


def test_capacity_iri_strips_capacity_prefix():
    iri = capacity_iri("capacity:perception", "text.space_split")
    assert iri == "capacity:perception:text.space_split"


def test_capacity_iri_rejects_bad_name():
    with pytest.raises(ValueError):
        capacity_iri("perception", "Text.BadCase")


def test_datastate_iri():
    iri = datastate_iri("text.raw")
    assert iri == "datastate:text.raw"
    assert parse_datastate_iri(iri) == "text.raw"


def test_datastate_iri_rejects_bad_name():
    with pytest.raises(ValueError):
        datastate_iri("Bad!Name")


def test_falkor_graph_name_global_vs_local():
    assert falkor_graph_name(None) == GLOBAL_FALKOR_GRAPH
    assert falkor_graph_name("alice") == LOCAL_FALKOR_GRAPH_FMT.format(user_slug="alice")


def test_slugify_sanitises_special_chars():
    assert slugify_user_id("alice@example.com") == "alice_example_com"
    with pytest.raises(ValueError):
        slugify_user_id("")


def test_functional_categories_contains_all_twelve():
    assert CATEGORY_PERCEPTION in FUNCTIONAL_CATEGORIES
    assert len(FUNCTIONAL_CATEGORIES) == 12
