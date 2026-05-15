"""XRefRepository integration tests — round-trip via live FalkorDB."""

from __future__ import annotations

import pytest

from mindsos_core.cypher.builders import build_create_metagraph_anchor
from mindsos_core.models.xref import XRef
from mindsos_core.persistence.xref_repository import XRefRepository

pytestmark = pytest.mark.integration


def _seed_anchor(client, mid: str, name: str) -> None:
    q, p = build_create_metagraph_anchor(mid, name, props_json="{}")
    client.run_query(q, p)


def test_persist_round_trip_full_xref(falkor_client):
    """End-to-end persist + read back via direct Cypher."""
    _seed_anchor(falkor_client, "mg-int-1", "int-1")
    x = XRef(
        source_metagraph_id="mg-int-1",
        source_id="src-1",
        target_metagraph_id="mg-tgt-int",
        target_role="lexicon",
        target_id="tgt-1",
        ref_type="SPECIALISES",
        xref_id="xid-int-1",
    )
    XRefRepository(falkor_client).persist(x)

    # Read back.
    res = falkor_client.run_query(
        "MATCH (x:XRef {id: $xid}) RETURN x.source_id AS sid, "
        "x.target_id AS tid, x.ref_type AS rt",
        {"xid": "xid-int-1"},
    )
    assert res.rows
    row = res.rows[0]
    assert row["sid"] == "src-1"
    assert row["tid"] == "tgt-1"
    assert row["rt"] == "SPECIALISES"


def test_xref_of_edge_links_to_metagraph_anchor(falkor_client):
    """M2 — :XREF_OF edge links the row to the source Metagraph anchor."""
    _seed_anchor(falkor_client, "mg-int-2", "int-2")
    x = XRef(
        source_metagraph_id="mg-int-2",
        source_id="src",
        target_metagraph_id="mg-tgt",
        target_role="r",
        target_id="t",
        ref_type="SPECIALISES",
        xref_id="xid-int-2",
    )
    XRefRepository(falkor_client).persist(x)

    res = falkor_client.run_query(
        "MATCH (x:XRef {id: $xid})-[:XREF_OF]->(m:Metagraph) "
        "RETURN m.id AS mid",
        {"xid": "xid-int-2"},
    )
    assert res.rows
    assert res.rows[0]["mid"] == "mg-int-2"


def test_remove_round_trip(falkor_client):
    """remove() deletes the row + its :XREF_OF edge."""
    _seed_anchor(falkor_client, "mg-int-3", "int-3")
    x = XRef(
        source_metagraph_id="mg-int-3",
        source_id="src",
        target_metagraph_id="mg-tgt",
        target_role="r",
        target_id="t",
        ref_type="SPECIALISES",
        xref_id="xid-int-3",
    )
    repo = XRefRepository(falkor_client)
    repo.persist(x)
    repo.remove("xid-int-3", source_metagraph_id="mg-int-3")

    res = falkor_client.run_query(
        "MATCH (x:XRef {id: $xid}) RETURN count(x) AS n",
        {"xid": "xid-int-3"},
    )
    assert res.rows[0]["n"] == 0


def test_persist_emits_committed_walentry(falkor_client):
    """M16 — successful persist commits its :WALEntry row."""
    _seed_anchor(falkor_client, "mg-int-4", "int-4")
    x = XRef(
        source_metagraph_id="mg-int-4",
        source_id="src",
        target_metagraph_id="mg-tgt",
        target_role="r",
        target_id="t",
        ref_type="SPECIALISES",
        xref_id="xid-int-4",
    )
    XRefRepository(falkor_client).persist(x)

    # All WAL entries for this metagraph should be committed=true.
    res = falkor_client.run_query(
        "MATCH (w:WALEntry {metagraph_id: $mid}) "
        "WHERE w.kind = 'xref_add' "
        "RETURN w.committed AS committed",
        {"mid": "mg-int-4"},
    )
    assert res.rows
    assert all(row["committed"] for row in res.rows)
