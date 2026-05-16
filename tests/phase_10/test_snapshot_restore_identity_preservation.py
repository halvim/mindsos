"""ADR-0027 mutate-in-place — id(mg), id(identity), id(graph) preserved on restore."""

from __future__ import annotations

from mindsos_core import Graph, Metagraph, MetagraphSnapshot

from tests._shared.soft_delete_fixture import make_metagraph_with_soft_delete


def test_metagraph_object_identity_preserved() -> None:
    mg, _ = make_metagraph_with_soft_delete()
    mg_oid = id(mg)
    snap = MetagraphSnapshot.of(mg)
    mg.properties["new"] = "x"
    snap.restore_into(mg)
    assert id(mg) == mg_oid


def test_identity_registry_object_preserved() -> None:
    mg, _ = make_metagraph_with_soft_delete()
    ident_oid = id(mg.identity)
    snap = MetagraphSnapshot.of(mg)
    snap.restore_into(mg)
    assert id(mg.identity) == ident_oid


def test_survivor_graph_object_preserved() -> None:
    mg, ids = make_metagraph_with_soft_delete()
    gid = ids["graph_ont"]
    g_oid = id(mg.graphs[gid])
    snap = MetagraphSnapshot.of(mg)
    # Mutate a property on the live graph; snapshot restore should revert AND
    # preserve the same Graph object identity.
    mg.graphs[gid].properties["mutated"] = True
    snap.restore_into(mg)
    assert id(mg.graphs[gid]) == g_oid


def test_metagraph_id_mismatch_raises() -> None:
    mg1, _ = make_metagraph_with_soft_delete()
    snap = MetagraphSnapshot.of(mg1)
    mg2 = Metagraph(name="other")
    try:
        snap.restore_into(mg2)
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "metagraph_id" in str(e)
