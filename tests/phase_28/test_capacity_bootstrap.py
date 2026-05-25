"""Phase 28 — bootstrap helpers (verbatim port from parent tests_l3/unit/test_bootstrap.py)."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CATEGORY_PATH_FINDING,
    CATEGORY_PERCEPTION,
    FUNCTIONAL_CATEGORIES,
    GLOBAL_METAGRAPH_NAME,
    ROLE_DATASTATES,
    category_role,
    create_global,
    create_local,
    ensure_category_graph,
    ensure_datastate_graph,
)


def test_create_global_has_datastates_and_every_category():
    mg = create_global()
    assert mg.name == GLOBAL_METAGRAPH_NAME
    roles = {g.role for g in mg.graphs.values()}
    assert ROLE_DATASTATES in roles
    for cat in FUNCTIONAL_CATEGORIES:
        assert category_role(cat) in roles


def test_create_global_with_limited_categories():
    mg = create_global(categories=(CATEGORY_PERCEPTION, CATEGORY_PATH_FINDING))
    roles = {g.role for g in mg.graphs.values()}
    assert roles == {
        ROLE_DATASTATES,
        category_role(CATEGORY_PERCEPTION),
        category_role(CATEGORY_PATH_FINDING),
    }


def test_create_local_has_user_id():
    mg = create_local("alice")
    assert mg.user_id == "alice"
    assert mg.graphs == {}


def test_ensure_category_graph_is_idempotent():
    mg = create_local("alice")
    g1 = ensure_category_graph(mg, CATEGORY_PERCEPTION)
    g2 = ensure_category_graph(mg, CATEGORY_PERCEPTION)
    assert g1 is g2


def test_ensure_datastate_graph_creates_lazily():
    mg = create_local("alice")
    assert ensure_datastate_graph(mg).role == ROLE_DATASTATES
    assert ROLE_DATASTATES in {g.role for g in mg.graphs.values()}


def test_create_local_requires_user_id():
    with pytest.raises(ValueError):
        create_local("")
