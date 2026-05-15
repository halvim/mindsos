"""WAL recovery FIFO across kinds — RPB-1 (causal write-order replay)."""

from __future__ import annotations

import pytest
from uuid import uuid4

from mindsos_core.cypher.builders import build_create_metagraph_anchor
from mindsos_core.persistence.bootstrap import register_all_l1_replayers
from mindsos_core.persistence.wal import WriteAheadLog, recover

pytestmark = pytest.mark.integration


def test_recover_replays_in_started_at_order(falkor_client):
    """RPB-1 — FIFO across kinds. add then remove ⇒ replay in that order."""
    q, p = build_create_metagraph_anchor("mg-fifo", "fifo", props_json="{}")
    falkor_client.run_query(q, p)
    register_all_l1_replayers(falkor_client)

    wal = WriteAheadLog(falkor_client, "mg-fifo")

    # Add first.
    wal.begin(
        operation_id=str(uuid4()),
        kind="xref_add",
        payload={
            "xref_id": "xid-fifo",
            "source_metagraph_id": "mg-fifo",
            "source_id": "s1",
            "target_metagraph_id": "mg-tgt",
            "target_role": "r",
            "target_id": "t1",
            "ref_type": "SPECIALISES",
            "properties": {},
        },
    )
    # Remove second.
    wal.begin(
        operation_id=str(uuid4()),
        kind="xref_remove",
        payload={"xref_id": "xid-fifo"},
    )

    n = recover(falkor_client, "mg-fifo")
    assert n == 2

    # Final state: row was added then removed → does not exist.
    res = falkor_client.run_query(
        "MATCH (x:XRef {id: 'xid-fifo'}) RETURN count(x) AS n"
    )
    assert res.rows[0]["n"] == 0
