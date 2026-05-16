"""Snapshot of an empty Metagraph (Phase 10 — ADR-0027 baseline)."""

from __future__ import annotations

from mindsos_core import Metagraph, MetagraphSnapshot, SoftDeleteKind


def test_snapshot_of_empty_metagraph() -> None:
    mg = Metagraph(name="empty")
    snap = MetagraphSnapshot.of(mg)
    assert snap._metagraph_id == mg.metagraph_id
    assert snap._metagraph_props == {}
    assert snap._graphs == {}
    assert snap._metaedges == {}
    assert snap._metahyperedges == {}
    assert snap._intergraph_edges == {}
    assert snap._intergraph_hyperedges == {}
    assert snap._schema_name is None
    assert snap._schema is None
    assert snap._xrefs == {}
    assert snap._xrefs_dirty == set()
    assert all(snap._soft_delete_dirty[k] == set() for k in SoftDeleteKind)
    assert mg.metagraph_id in snap._identity_ids


def test_restore_empty_roundtrip() -> None:
    mg = Metagraph(name="empty")
    snap = MetagraphSnapshot.of(mg)
    mg.properties["k"] = "v"
    snap.restore_into(mg)
    assert mg.properties == {}
