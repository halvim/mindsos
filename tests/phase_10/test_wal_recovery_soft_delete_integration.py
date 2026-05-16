"""WAL recovery for Phase 10 kinds — uncommitted entry → recover → DB state correct."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from mindsos_core.cypher.builders import build_create_metagraph_anchor, build_create_xref
from mindsos_core.persistence.bootstrap import bootstrap, register_all_l1_replayers
from mindsos_core.persistence.wal import recover

pytestmark = pytest.mark.integration


def _seed_metagraph_and_xref(client, mid: str, xid: str) -> None:
    """Set up an :Metagraph anchor + an :XRef row directly via builders."""
    bootstrap(client)
    q, p = build_create_metagraph_anchor(mid, "wal-recover-test", props_json="{}")
    client.run_query(q, p)
    q, p = build_create_xref(
        xref_id=xid,
        source_metagraph_id=mid,
        source_id="src",
        target_metagraph_id="tmg",
        target_role="ont",
        target_id="tid",
        ref_type="SPECIALISES",
        properties={},
    )
    client.run_query(q, p)


def _write_uncommitted_wal_entry(client, mid: str, kind: str, payload: dict) -> str:
    """Insert an uncommitted :WALEntry row using the Phase 09 field names.

    Schema per wal.py:WriteAheadLog.entry — properties are
    ``operation_id``, ``metagraph_id``, ``kind``, ``payload_json`` (JSON
    string), ``started_at`` (ISO string), ``committed`` (bool).
    """
    op_id = str(uuid4())
    payload_json = json.dumps(payload or {}, sort_keys=True)
    started_at = datetime.now(timezone.utc).isoformat()
    client.run_query(
        "MATCH (m:Metagraph {id: $mid}) "
        "CREATE (m)<-[:IN_METAGRAPH]-(:WALEntry {"
        "  operation_id: $oid, metagraph_id: $mid, kind: $kind, "
        "  payload_json: $payload_json, started_at: $started_at, "
        "  committed: false})",
        {"mid": mid, "oid": op_id, "kind": kind,
         "payload_json": payload_json, "started_at": started_at},
    )
    return op_id


def test_xref_mark_stale_wal_recover(falkor_client):
    """Write uncommitted xref_mark_stale entry → recover → target_stale=True in DB."""
    mid = "mg-wal-recover-stale"
    xid = "xref-wal-recover-1"
    _seed_metagraph_and_xref(falkor_client, mid, xid)
    register_all_l1_replayers(falkor_client)

    _write_uncommitted_wal_entry(
        falkor_client, mid, "xref_mark_stale", {"xref_id": xid},
    )
    recover(falkor_client, mid)

    res = falkor_client.run_query(
        "MATCH (x:XRef {id: $xid}) RETURN x.target_stale AS stale",
        {"xid": xid},
    )
    assert res.rows
    assert bool(res.rows[0]["stale"]) is True


def test_unknown_wal_kind_raises_replayer_missing(falkor_client):
    """Phase 09 P62 carry — uncommitted entry with unknown kind raises."""
    from mindsos_core.exceptions import WALReplayerMissingError

    mid = "mg-wal-unknown-kind"
    bootstrap(falkor_client)
    q, p = build_create_metagraph_anchor(mid, "unknown-kind", props_json="{}")
    falkor_client.run_query(q, p)
    register_all_l1_replayers(falkor_client)

    _write_uncommitted_wal_entry(
        falkor_client, mid, "never_registered", {},
    )
    try:
        recover(falkor_client, mid)
        raise AssertionError("expected WALReplayerMissingError")
    except WALReplayerMissingError:
        pass
