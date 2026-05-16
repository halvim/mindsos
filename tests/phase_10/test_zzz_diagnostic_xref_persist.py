"""Diagnostic — does add_xref + persist actually write :XRef to DB?

If this test fails, the bug is in the substrate (persist drain doesn't
write XRef). If it passes, the bug is downstream in load.
"""

from __future__ import annotations

import pytest

from mindsos_core import Graph, Metagraph
from mindsos_core.persistence import MetagraphRepository
from mindsos_core.persistence.bootstrap import bootstrap

pytestmark = pytest.mark.integration


def test_diagnostic_add_xref_persist_writes_to_db(falkor_client):
    bootstrap(falkor_client)
    mg = Metagraph(name="diag")
    g = Graph(name="g", role="ont")
    mg.add_graph(g)
    n1 = g.add_node(value="a", type_name="Person")
    x = mg.add_xref(
        source_id=n1.node_id,
        target_metagraph_id="other",
        target_role="ont",
        target_id="tid",
        ref_type="SPECIALISES",
    )
    assert x.xref_id in mg._xrefs_dirty, "xref should be in _xrefs_dirty before persist"
    assert x.xref_id in mg.xrefs

    MetagraphRepository(falkor_client).persist(mg)

    # Direct DB query — does the :XRef row exist?
    res = falkor_client.run_query(
        "MATCH (x:XRef {id: $xid}) "
        "RETURN x.id AS id, x.source_metagraph_id AS smid, "
        "       x.target_stale AS stale",
        {"xid": x.xref_id},
    )
    assert res.rows, f"NO :XRef row found for id={x.xref_id!r} after persist"
    row = res.rows[0]
    assert row["id"] == x.xref_id
    assert row["smid"] == mg.metagraph_id


def test_diagnostic_mark_stale_persists_target_stale(falkor_client):
    bootstrap(falkor_client)
    mg = Metagraph(name="diag2")
    g = Graph(name="g", role="ont")
    mg.add_graph(g)
    n1 = g.add_node(value="a", type_name="Person")
    x = mg.add_xref(
        source_id=n1.node_id, target_metagraph_id="other",
        target_role="ont", target_id="tid", ref_type="SPECIALISES",
    )
    mg.mark_xref_stale(x.xref_id)

    MetagraphRepository(falkor_client).persist(mg)

    res = falkor_client.run_query(
        "MATCH (x:XRef {id: $xid}) RETURN x.target_stale AS stale",
        {"xid": x.xref_id},
    )
    assert res.rows, "XRef row missing in DB after persist+mark_stale"
    stale = res.rows[0]["stale"]
    assert stale is True or stale == 1 or stale == "true", (
        f"target_stale not stamped: got {stale!r} (type={type(stale).__name__})"
    )


def test_diagnostic_xref_query_by_source_metagraph_id(falkor_client):
    """Does the XRefLoader-style query (MATCH by source_metagraph_id) find the row?"""
    bootstrap(falkor_client)
    mg = Metagraph(name="diag3")
    g = Graph(name="g", role="ont")
    mg.add_graph(g)
    n1 = g.add_node(value="a", type_name="Person")
    x = mg.add_xref(
        source_id=n1.node_id, target_metagraph_id="other",
        target_role="ont", target_id="tid", ref_type="SPECIALISES",
    )
    MetagraphRepository(falkor_client).persist(mg)

    # Mirror XRefLoader._fetch_xrefs query.
    res = falkor_client.run_query(
        "MATCH (x:XRef {source_metagraph_id: $mid}) RETURN x.id AS id",
        {"mid": mg.metagraph_id},
    )
    assert res.rows, (
        f"XRefLoader-style query found no rows for source_metagraph_id="
        f"{mg.metagraph_id!r}; xref.source_metagraph_id was {x.source_metagraph_id!r}"
    )
    assert any(r["id"] == x.xref_id for r in res.rows)
