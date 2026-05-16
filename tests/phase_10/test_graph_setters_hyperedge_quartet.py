"""SD1 fix — Graph.deprecate_hyperedge quartet (v3 baseline lacked this API)."""

from __future__ import annotations

from mindsos_core import Graph, IdentityError, SoftDeleteKind


def _g_with_he() -> tuple[Graph, str]:
    g = Graph(name="t")
    n1 = g.add_node(value="a", type_name="Person")
    n2 = g.add_node(value="b", type_name="Person")
    he = g.add_hyperedge(nodes={n1, n2}, type_name="LINKS")
    return g, he.edge_id


def test_deprecate_hyperedge() -> None:
    g, hid = _g_with_he()
    he = g.deprecate_hyperedge(hid)
    assert he.deprecated_at is not None
    assert hid in g._soft_delete_dirty[SoftDeleteKind.HYPEREDGE]


def test_undeprecate_hyperedge() -> None:
    g, hid = _g_with_he()
    g.deprecate_hyperedge(hid)
    he = g.undeprecate_hyperedge(hid)
    assert he.deprecated_at is None


def test_dispute_hyperedge() -> None:
    g, hid = _g_with_he()
    he = g.dispute_hyperedge(hid)
    assert he.disputed_at is not None


def test_undispute_hyperedge() -> None:
    g, hid = _g_with_he()
    g.dispute_hyperedge(hid)
    he = g.undispute_hyperedge(hid)
    assert he.disputed_at is None


def test_unknown_hyperedge_id_raises() -> None:
    g = Graph(name="t")
    for fn in (g.deprecate_hyperedge, g.undeprecate_hyperedge,
               g.dispute_hyperedge, g.undispute_hyperedge):
        try:
            fn("nope")
            raise AssertionError(f"{fn.__name__} should raise IdentityError")
        except IdentityError:
            pass
