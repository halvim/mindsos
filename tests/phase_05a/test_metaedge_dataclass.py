"""Phase 05a — MetaEdge / MetaHyperEdge dataclass invariants (P8 + P9 + P15)."""

from __future__ import annotations

import pytest

from mindsos_core import (
    CypherError,
    MetaEdge,
    MetaHyperEdge,
    SchemaError,
)


# ── MetaEdge __post_init__ regex (P9) ────────────────────────────────────────


def test_metaedge_post_init_rejects_lowercase_type():
    """P9 — MetaEdge.__post_init__ runs ADR-0021 cypher rel-type regex."""
    with pytest.raises(CypherError):
        MetaEdge(
            source_graph_id="g1-id",
            target_graph_id="g2-id",
            type_name="lowercase_type",  # invalid
        )


def test_metaedge_post_init_accepts_uppercase_type():
    """Valid uppercase rel-type passes."""
    me = MetaEdge(
        source_graph_id="g1-id",
        target_graph_id="g2-id",
        type_name="REFINES",
    )
    assert me.type_name == "REFINES"


def test_metaedge_post_init_rejects_invalid_first_char():
    """First char must be uppercase letter (ADR-0021)."""
    with pytest.raises(CypherError):
        MetaEdge(
            source_graph_id="g1",
            target_graph_id="g2",
            type_name="3_LEADING_DIGIT",
        )


# ── MetaHyperEdge __post_init__ regex (P9) + cardinality (P15) ───────────────


def test_metahyperedge_post_init_rejects_lowercase_type():
    """P9 — MetaHyperEdge regex enforced at dataclass boundary."""
    with pytest.raises(CypherError):
        MetaHyperEdge(
            graph_ids=["g1-id", "g2-id"],
            type_name="lowercase",
        )


def test_metahyperedge_refuses_single_member():
    """P15 — n=1 metahyperedge rejected as degenerate."""
    with pytest.raises(SchemaError, match="at least 2"):
        MetaHyperEdge(
            graph_ids=["only-one"],
            type_name="X",
        )


def test_metahyperedge_refuses_empty():
    """P15 — n=0 metahyperedge rejected."""
    with pytest.raises(SchemaError):
        MetaHyperEdge(graph_ids=[], type_name="X")


def test_metahyperedge_refuses_duplicate_members():
    """A graph cannot appear twice in member set."""
    with pytest.raises(SchemaError, match="unique"):
        MetaHyperEdge(
            graph_ids=["g1", "g1", "g2"],
            type_name="X",
        )


def test_metahyperedge_accepts_two_members():
    """Minimum n=2 case (P15 boundary)."""
    mhe = MetaHyperEdge(
        graph_ids=["g1", "g2"],
        type_name="REL",
    )
    assert mhe.graph_ids == ["g1", "g2"]
    assert mhe.type_name == "REL"


# ── kw_only dataclass (P8) ───────────────────────────────────────────────────


def test_metaedge_kw_only_rejects_positional():
    """P8 — kw_only=True; positional args raise TypeError."""
    with pytest.raises(TypeError):
        MetaEdge("g1", "g2", "REL")  # type: ignore[misc]


def test_metahyperedge_kw_only_rejects_positional():
    """P8 — kw_only=True symmetric on MetaHyperEdge."""
    with pytest.raises(TypeError):
        MetaHyperEdge(["g1", "g2"], "REL")  # type: ignore[misc]


# ── soft-delete fields stripped (P1) ─────────────────────────────────────────


def test_metaedge_no_deprecated_at_field():
    """P1 — soft-delete substrate stripped in 05a; lands uniformly in P10."""
    me = MetaEdge(
        source_graph_id="g1",
        target_graph_id="g2",
        type_name="REL",
    )
    assert not hasattr(me, "deprecated_at")
    assert not hasattr(me, "disputed_at")


def test_metahyperedge_no_deprecated_at_field():
    """P1 — symmetric on MetaHyperEdge."""
    mhe = MetaHyperEdge(graph_ids=["g1", "g2"], type_name="REL")
    assert not hasattr(mhe, "deprecated_at")
    assert not hasattr(mhe, "disputed_at")
