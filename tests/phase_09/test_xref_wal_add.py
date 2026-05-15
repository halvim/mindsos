"""WAL add — M16 :WALEntry write + commit on success."""

from __future__ import annotations

import pytest

from mindsos_core.cypher.builders import build_create_metagraph_anchor
from mindsos_core.models.xref import XRef
from mindsos_core.persistence.xref_repository import XRefRepository

pytestmark = pytest.mark.integration


def test_persist_writes_xref_add_walentry(falkor_client):
    """M16 — :WALEntry kind='xref_add' is created during persist."""
    q, p = build_create_metagraph_anchor("mg-wal-add", "wal-add", props_json="{}")
    falkor_client.run_query(q, p)

    XRefRepository(falkor_client).persist(XRef(
        source_metagraph_id="mg-wal-add", source_id="s1",
        target_metagraph_id="mg-tgt", target_role="r", target_id="t1",
        ref_type="SPECIALISES", xref_id="xid-wal-1",
    ))

    res = falkor_client.run_query(
        "MATCH (w:WALEntry {kind: 'xref_add', metagraph_id: $mid}) "
        "RETURN count(w) AS n",
        {"mid": "mg-wal-add"},
    )
    assert res.rows[0]["n"] == 1


def test_walentry_committed_after_persist(falkor_client):
    q, p = build_create_metagraph_anchor("mg-wal-c", "wal-c", props_json="{}")
    falkor_client.run_query(q, p)

    XRefRepository(falkor_client).persist(XRef(
        source_metagraph_id="mg-wal-c", source_id="s1",
        target_metagraph_id="mg-tgt", target_role="r", target_id="t1",
        ref_type="SPECIALISES", xref_id="xid-wal-c",
    ))

    res = falkor_client.run_query(
        "MATCH (w:WALEntry {kind: 'xref_add', metagraph_id: $mid}) "
        "WHERE w.committed = false RETURN count(w) AS n",
        {"mid": "mg-wal-c"},
    )
    assert res.rows[0]["n"] == 0
