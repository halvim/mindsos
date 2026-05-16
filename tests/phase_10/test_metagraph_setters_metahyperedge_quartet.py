"""SD2 + SD3 fix — Metagraph metahyperedge quartet."""

from __future__ import annotations

from mindsos_core import Graph, IdentityError, Metagraph, SoftDeleteKind


def _mg_with_mhe() -> tuple[Metagraph, str]:
    mg = Metagraph(name="t")
    g1, g2, g3 = Graph(name="g1"), Graph(name="g2"), Graph(name="g3")
    mg.add_graph(g1); mg.add_graph(g2); mg.add_graph(g3)
    mhe = mg.add_metahyperedge(
        graph_ids=[g1.graph_id, g2.graph_id, g3.graph_id], type_name="X")
    return mg, mhe.edge_id


def test_deprecate_metahyperedge() -> None:
    mg, mhid = _mg_with_mhe()
    mhe = mg.deprecate_metahyperedge(mhid)
    assert mhe.deprecated_at is not None
    assert mhid in mg._soft_delete_dirty[SoftDeleteKind.METAHYPEREDGE]


def test_undeprecate_metahyperedge() -> None:
    mg, mhid = _mg_with_mhe()
    mg.deprecate_metahyperedge(mhid)
    mhe = mg.undeprecate_metahyperedge(mhid)
    assert mhe.deprecated_at is None


def test_dispute_metahyperedge() -> None:
    mg, mhid = _mg_with_mhe()
    mhe = mg.dispute_metahyperedge(mhid)
    assert mhe.disputed_at is not None


def test_undispute_metahyperedge() -> None:
    mg, mhid = _mg_with_mhe()
    mg.dispute_metahyperedge(mhid)
    mhe = mg.undispute_metahyperedge(mhid)
    assert mhe.disputed_at is None


def test_unknown_metahyperedge_id_raises() -> None:
    mg = Metagraph(name="t")
    for fn in (mg.deprecate_metahyperedge, mg.undeprecate_metahyperedge,
               mg.dispute_metahyperedge, mg.undispute_metahyperedge):
        try:
            fn("nope")
            raise AssertionError("expected IdentityError")
        except IdentityError:
            pass
