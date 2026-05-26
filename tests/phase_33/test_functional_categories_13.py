"""Phase 33 — FUNCTIONAL_CATEGORIES extended to 13 (R0 PB-6)."""

from __future__ import annotations

from mindsos_capacity import (
    CATEGORY_CONSOLIDATE,
    FUNCTIONAL_CATEGORIES,
    CapacityLayer,
)


def test_functional_categories_count_is_13():
    assert len(FUNCTIONAL_CATEGORIES) == 13


def test_category_consolidate_is_member():
    assert CATEGORY_CONSOLIDATE == "consolidate"
    assert CATEGORY_CONSOLIDATE in FUNCTIONAL_CATEGORIES


def test_create_global_produces_14_graphs():
    """13 categories + 1 capacity:datastates shared graph = 14."""
    layer = CapacityLayer()
    mg = layer.global_metagraph()
    assert len(mg.graphs) == 14
    roles = {g.role for g in mg.graphs.values()}
    assert "capacity:consolidate" in roles
    assert "capacity:datastates" in roles


def test_existing_12_categories_still_present():
    """No regression on pre-Phase-33 categories."""
    expected = {
        "perception", "comprehension", "derivation", "decomposition",
        "combination", "path-finding", "retrieval", "scoring", "trace",
        "signalling", "interaction", "learning-methods",
    }
    assert expected.issubset(FUNCTIONAL_CATEGORIES)
