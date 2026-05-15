"""WAL remove — DETACH DELETE replayer (PB-8 + M16)."""

from __future__ import annotations

import pytest
from uuid import uuid4

from mindsos_core.cypher.builders import build_create_metagraph_anchor
from mindsos_core.models.xref import XRef
from mindsos_core.persistence.bootstrap import register_all_l1_replayers
from mindsos_core.persistence.wal import WriteAheadLog, recover
from mindsos_core.persistence.xref_repository import XRefRepository

pytestmark = pytest.mark.integration


def test_remove_writes_xref_remove_walentry(falkor_client):
    q, p = build_create_metagraph_anchor("mg-wr", "wr", props_json="{}")
    falkor_client.run_query(q, p)
    repo = XRefRepository(falkor_client)
    repo.persist(XRef(
        source_metagraph_id="mg-wr", source_id="s1",
        target_metagraph_id="mg-tgt", target_role="r", target_id="t1",
        ref_type="SPECIALISES", xref_id="xid-wr",
    ))
    repo.remove("xid-wr", source_metagraph_id="mg-wr")

    # WAL has a committed xref_remove entry.
    res = falkor_client.run_query(
        "MATCH (w:WALEntry {kind: 'xref_remove', metagraph_id: $mid}) "
        "RETURN count(w) AS n, min(w.committed) AS c",
        {"mid": "mg-wr"},
    )
    assert res.rows[0]["n"] == 1


def test_recovery_replays_uncommitted_xref_remove(falkor_client):
    """Simulate remove crash; recover() runs DETACH DELETE; idempotent on missing row."""
    q, p = build_create_metagraph_anchor("mg-wrr", "wrr", props_json="{}")
    falkor_client.run_query(q, p)
    register_all_l1_replayers(falkor_client)

    repo = XRefRepository(falkor_client)
    repo.persist(XRef(
        source_metagraph_id="mg-wrr", source_id="s1",
        target_metagraph_id="mg-tgt", target_role="r", target_id="t1",
        ref_type="SPECIALISES", xref_id="xid-wrr",
    ))

    # Simulate crash mid-remove: WAL begin without commit.
    wal = WriteAheadLog(falkor_client, "mg-wrr")
    op_id = str(uuid4())
    wal.begin(
        operation_id=op_id, kind="xref_remove",
        payload={"xref_id": "xid-wrr"},
    )

    # XRef still exists (DETACH DELETE not yet run).
    pre = falkor_client.run_query(
        "MATCH (x:XRef {id: 'xid-wrr'}) RETURN count(x) AS n"
    )
    assert pre.rows[0]["n"] == 1

    n = recover(falkor_client, "mg-wrr")
    assert n == 1

    post = falkor_client.run_query(
        "MATCH (x:XRef {id: 'xid-wrr'}) RETURN count(x) AS n"
    )
    assert post.rows[0]["n"] == 0
