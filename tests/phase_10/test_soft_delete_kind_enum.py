"""P72 — SoftDeleteKind str-Enum (typo-proof dirty-bucket keys)."""

from __future__ import annotations

from mindsos_core import SoftDeleteKind


def test_softdeletekind_5_values() -> None:
    expected = {"edge", "hyperedge", "metaedge", "metahyperedge", "xref"}
    actual = {k.value for k in SoftDeleteKind}
    assert actual == expected


def test_softdeletekind_str_enum_behavior() -> None:
    """Subclasses str → comparable to plain string literals."""
    assert SoftDeleteKind.EDGE == "edge"
    assert SoftDeleteKind.METAHYPEREDGE == "metahyperedge"


def test_softdeletekind_used_in_metagraph_dirty_keys() -> None:
    from mindsos_core import Metagraph
    mg = Metagraph(name="t")
    assert set(mg._soft_delete_dirty.keys()) == set(SoftDeleteKind)


def test_softdeletekind_used_in_graph_dirty_keys() -> None:
    """P86 — Graph carries only EDGE + HYPEREDGE buckets."""
    from mindsos_core import Graph
    g = Graph(name="t")
    assert set(g._soft_delete_dirty.keys()) == {SoftDeleteKind.EDGE, SoftDeleteKind.HYPEREDGE}
