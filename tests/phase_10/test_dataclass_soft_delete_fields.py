"""M5 — Edge/HyperEdge/MetaEdge/MetaHyperEdge gain deprecated_at + disputed_at."""

from __future__ import annotations

from dataclasses import fields

from mindsos_core import Edge, HyperEdge, MetaEdge, MetaHyperEdge


def test_edge_has_soft_delete_fields() -> None:
    names = {f.name for f in fields(Edge)}
    assert "deprecated_at" in names
    assert "disputed_at" in names


def test_hyperedge_has_soft_delete_fields() -> None:
    names = {f.name for f in fields(HyperEdge)}
    assert "deprecated_at" in names
    assert "disputed_at" in names


def test_metaedge_has_soft_delete_fields() -> None:
    names = {f.name for f in fields(MetaEdge)}
    assert "deprecated_at" in names
    assert "disputed_at" in names


def test_metahyperedge_has_soft_delete_fields() -> None:
    names = {f.name for f in fields(MetaHyperEdge)}
    assert "deprecated_at" in names
    assert "disputed_at" in names


def test_defaults_are_none() -> None:
    from mindsos_core.models.node import Node
    n1 = Node(value="a", type_name="Person")
    n2 = Node(value="b", type_name="Person")
    e = Edge(source=n1, target=n2, type_name="KNOWS")
    assert e.deprecated_at is None and e.disputed_at is None

    he = HyperEdge(nodes={n1, n2}, type_name="LINKS")
    assert he.deprecated_at is None and he.disputed_at is None

    me = MetaEdge(source_graph_id="g1", target_graph_id="g2", type_name="X")
    assert me.deprecated_at is None and me.disputed_at is None

    mhe = MetaHyperEdge(graph_ids=["g1", "g2"], type_name="X")
    assert mhe.deprecated_at is None and mhe.disputed_at is None
