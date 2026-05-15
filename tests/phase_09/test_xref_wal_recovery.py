"""WAL recovery — M16 + PB-8 (MERGE-based replayer recovers crashed write)."""

from __future__ import annotations

import pytest
from uuid import uuid4

from mindsos_core.cypher.builders import build_create_metagraph_anchor
from mindsos_core.persistence.bootstrap import register_all_l1_replayers
from mindsos_core.persistence.wal import WriteAheadLog, recover

pytestmark = pytest.mark.integration


def test_recovery_replays_uncommitted_xref_add(falkor_client):
    """Simulate crash: WAL begin without commit; recover() replays via MERGE."""
    q, p = build_create_metagraph_anchor("mg-rec", "rec", props_json="{}")
    falkor_client.run_query(q, p)

    # falkor_client already has replayers registered via FalkorClient.__init__,
    # but the falkor_client fixture might be the InMemoryClient-style;
    # register defensively (idempotent overwrite).
    register_all_l1_replayers(falkor_client)

    # Simulate crash: write a begin entry, NEVER commit.
    wal = WriteAheadLog(falkor_client, "mg-rec")
    op_id = str(uuid4())
    payload = {
        "xref_id": "xid-recovery",
        "source_metagraph_id": "mg-rec",
        "source_id": "s1",
        "target_metagraph_id": "mg-tgt",
        "target_role": "r",
        "target_id": "t1",
        "ref_type": "SPECIALISES",
        "properties": {},
    }
    wal.begin(operation_id=op_id, kind="xref_add", payload=payload)

    # XRef row does NOT exist yet (we only wrote the begin entry).
    pre = falkor_client.run_query(
        "MATCH (x:XRef {id: 'xid-recovery'}) RETURN count(x) AS n"
    )
    assert pre.rows[0]["n"] == 0

    # Recover.
    n = recover(falkor_client, "mg-rec")
    assert n == 1

    # XRef row now exists.
    post = falkor_client.run_query(
        "MATCH (x:XRef {id: 'xid-recovery'}) RETURN count(x) AS n"
    )
    assert post.rows[0]["n"] == 1


def test_recovery_idempotent_re_recover(falkor_client):
    """PB-8 — MERGE-based replayer; re-recover after success is a no-op."""
    q, p = build_create_metagraph_anchor("mg-idem", "idem", props_json="{}")
    falkor_client.run_query(q, p)
    register_all_l1_replayers(falkor_client)

    wal = WriteAheadLog(falkor_client, "mg-idem")
    op_id = str(uuid4())
    payload = {
        "xref_id": "xid-idem",
        "source_metagraph_id": "mg-idem",
        "source_id": "s1",
        "target_metagraph_id": "mg-tgt",
        "target_role": "r",
        "target_id": "t1",
        "ref_type": "SPECIALISES",
        "properties": {},
    }
    wal.begin(operation_id=op_id, kind="xref_add", payload=payload)
    recover(falkor_client, "mg-idem")
    # Second recover returns 0 (entry already committed).
    assert recover(falkor_client, "mg-idem") == 0
