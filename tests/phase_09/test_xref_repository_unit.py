"""XRefRepository unit tests — InMemoryClient asserts emitted Cypher (M16 + PB-8)."""

from __future__ import annotations

from mindsos_core.models.xref import XRef
from mindsos_core.persistence import InMemoryClient
from mindsos_core.persistence.xref_repository import XRefRepository


def _make_xref() -> XRef:
    return XRef(
        source_metagraph_id="mg-src",
        source_id="src-n1",
        target_metagraph_id="mg-tgt",
        target_role="lexicon",
        target_id="tgt-n1",
        ref_type="SPECIALISES",
        xref_id="xid-1",
    )


def test_persist_emits_wal_begin_then_create_then_commit():
    """M16 + PB-8 — wal.entry context wraps build_create_xref MERGE."""
    c = InMemoryClient()
    # Begin WAL entry returns op_id.
    c.script([{"op_id": "ignored"}])  # WAL begin
    c.script([{"id": "xid-1"}])        # build_create_xref MERGE
    c.script([{"op_id": "ignored"}])  # WAL commit

    repo = XRefRepository(c)
    repo.persist(_make_xref())

    # 3 queries emitted: WAL begin (WALEntry), MERGE :XRef, WAL commit.
    queries = [q for q, _ in c.calls]
    assert any("WALEntry" in q for q in queries), queries
    assert any("MERGE (x:XRef" in q for q in queries), queries
    assert any("XREF_OF" in q for q in queries), queries
    assert any("committed = true" in q for q in queries), queries


def test_remove_emits_wal_wrap_around_detach_delete():
    """PB-8 — DETACH DELETE for xref_remove."""
    c = InMemoryClient()
    c.script([{"op_id": "ignored"}])  # WAL begin
    c.script([{"id": "xid-1"}])        # DETACH DELETE
    c.script([{"op_id": "ignored"}])  # WAL commit

    repo = XRefRepository(c)
    repo.remove("xid-1", source_metagraph_id="mg-src")

    queries = [q for q, _ in c.calls]
    assert any("DETACH DELETE x" in q for q in queries), queries


def test_persist_payload_carries_8_fields_p53():
    """P53 — WAL payload has 8 fields; no target_stale / deprecated_at."""
    c = InMemoryClient()
    c.script([{"op_id": "ignored"}])  # WAL begin
    c.script([{"id": "xid-1"}])
    c.script([{"op_id": "ignored"}])

    repo = XRefRepository(c)
    repo.persist(_make_xref())

    # WAL begin call (first) carries payload_json.
    _q, params = c.calls[0]
    import json
    payload = json.loads(params["payload_json"])
    assert set(payload.keys()) == {
        "xref_id",
        "source_metagraph_id",
        "source_id",
        "target_metagraph_id",
        "target_role",
        "target_id",
        "ref_type",
        "properties",
    }
    assert "target_stale" not in payload
    assert "deprecated_at" not in payload
