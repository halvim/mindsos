"""M6 — Graph.deprecate_edge / undeprecate / dispute / undispute quartet."""

from __future__ import annotations

from datetime import datetime, timezone

from mindsos_core import Graph, IdentityError, SoftDeleteKind


def _g_with_edge() -> tuple[Graph, str]:
    g = Graph(name="t")
    n1 = g.add_node(value="a", type_name="Person")
    n2 = g.add_node(value="b", type_name="Person")
    e = g.add_edge(source=n1, target=n2, type_name="KNOWS")
    return g, e.edge_id


def test_deprecate_edge_sets_and_marks_dirty() -> None:
    g, eid = _g_with_edge()
    edge = g.deprecate_edge(eid)
    assert edge.deprecated_at is not None
    assert edge.deprecated_at.tzinfo is timezone.utc
    assert eid in g._soft_delete_dirty[SoftDeleteKind.EDGE]
    assert edge is g.edges[eid]


def test_undeprecate_edge_clears() -> None:
    g, eid = _g_with_edge()
    g.deprecate_edge(eid)
    edge = g.undeprecate_edge(eid)
    assert edge.deprecated_at is None
    assert eid in g._soft_delete_dirty[SoftDeleteKind.EDGE]


def test_dispute_edge_explicit_at() -> None:
    g, eid = _g_with_edge()
    explicit = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
    edge = g.dispute_edge(eid, at=explicit)
    assert edge.disputed_at == explicit


def test_undispute_edge_clears() -> None:
    g, eid = _g_with_edge()
    g.dispute_edge(eid)
    edge = g.undispute_edge(eid)
    assert edge.disputed_at is None


def test_unknown_id_raises_identity_error() -> None:
    g, _ = _g_with_edge()
    for fn in (g.deprecate_edge, g.undeprecate_edge, g.dispute_edge, g.undispute_edge):
        try:
            fn("nope")
            raise AssertionError(f"{fn.__name__} should raise IdentityError")
        except IdentityError:
            pass
