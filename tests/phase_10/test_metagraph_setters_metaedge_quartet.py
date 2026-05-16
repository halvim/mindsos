"""SD2 fix — Metagraph metaedge quartet (v3 baseline had single-overload setter)."""

from __future__ import annotations

from mindsos_core import Graph, IdentityError, Metagraph, SoftDeleteKind


def _mg_with_me() -> tuple[Metagraph, str]:
    mg = Metagraph(name="t")
    g1 = Graph(name="g1", role="ont"); g2 = Graph(name="g2", role="lex")
    mg.add_graph(g1); mg.add_graph(g2)
    me = mg.add_metaedge(source_graph_id=g1.graph_id, target_graph_id=g2.graph_id, type_name="X")
    return mg, me.edge_id


def test_deprecate_metaedge() -> None:
    mg, meid = _mg_with_me()
    me = mg.deprecate_metaedge(meid)
    assert me.deprecated_at is not None
    assert meid in mg._soft_delete_dirty[SoftDeleteKind.METAEDGE]


def test_undeprecate_metaedge() -> None:
    mg, meid = _mg_with_me()
    mg.deprecate_metaedge(meid)
    me = mg.undeprecate_metaedge(meid)
    assert me.deprecated_at is None


def test_dispute_metaedge_sd3_fix() -> None:
    """SD3 fix — v3 baseline had no dispute path on Metagraph quartet."""
    mg, meid = _mg_with_me()
    me = mg.dispute_metaedge(meid)
    assert me.disputed_at is not None


def test_undispute_metaedge() -> None:
    mg, meid = _mg_with_me()
    mg.dispute_metaedge(meid)
    me = mg.undispute_metaedge(meid)
    assert me.disputed_at is None


def test_unknown_metaedge_id_raises() -> None:
    mg = Metagraph(name="t")
    for fn in (mg.deprecate_metaedge, mg.undeprecate_metaedge,
               mg.dispute_metaedge, mg.undispute_metaedge):
        try:
            fn("nope")
            raise AssertionError(f"{fn.__name__} should raise IdentityError")
        except IdentityError:
            pass
