"""WAL replayer registration — RR-16 per-kind module + P51 per-Client."""

from __future__ import annotations

import pytest

from mindsos_core.exceptions import WALReplayerMissingError
from mindsos_core.persistence import InMemoryClient
from mindsos_core.persistence.bootstrap import register_all_l1_replayers
from mindsos_core.persistence.wal import (
    _get_replayers,
    clear_replayers,
    recover,
    register_replayer,
)
from mindsos_core.persistence.xref_repository import register_xref_replayers


def test_register_xref_replayers_adds_two_kinds():
    """RR-16 — per-kind module owns its registration; both kinds land."""
    c = InMemoryClient()
    register_xref_replayers(c)
    reg = _get_replayers(c)
    assert "xref_add" in reg
    assert "xref_remove" in reg


def test_register_all_l1_replayers_composes_xref():
    """RR-16 — central wrapper composes per-kind registration fns."""
    c = InMemoryClient()
    register_all_l1_replayers(c)
    reg = _get_replayers(c)
    assert "xref_add" in reg
    assert "xref_remove" in reg


def test_per_client_isolation_p51():
    """P51 — distinct clients have distinct replayer dicts."""
    c1 = InMemoryClient()
    c2 = InMemoryClient()
    register_xref_replayers(c1)
    # c2 has nothing registered.
    reg1 = _get_replayers(c1)
    reg2 = _get_replayers(c2)
    assert "xref_add" in reg1
    assert "xref_add" not in reg2


def test_clear_replayers_per_client():
    c = InMemoryClient()
    register_xref_replayers(c)
    clear_replayers(c)
    reg = _get_replayers(c)
    assert reg == {}


def test_replayer_closure_captures_client():
    """RR-16 — replayer body uses captured client (not threaded through)."""
    c = InMemoryClient()
    register_xref_replayers(c)

    # Trigger the xref_add replayer with a script set up so the
    # MERGE round-trip succeeds.
    c.script([{"id": "xid-1"}])  # MERGE :XRef return.

    payload = {
        "xref_id": "xid-1",
        "source_metagraph_id": "mg-src",
        "source_id": "n1",
        "target_metagraph_id": "mg-tgt",
        "target_role": "lex",
        "target_id": "t1",
        "ref_type": "SPECIALISES",
        "properties": {},
    }
    replay_fn = _get_replayers(c)["xref_add"]
    replay_fn(payload)
    queries = [q for q, _ in c.calls]
    assert any("MERGE (x:XRef" in q for q in queries)


def test_recover_finds_xref_add_replayer_after_register_all():
    """End-to-end — register_all_l1_replayers makes recover() find replayers."""
    c = InMemoryClient()
    register_all_l1_replayers(c)
    # Empty WAL → no work but no raise either.
    c.script([])  # list_uncommitted returns nothing.
    n = recover(c, "mg-1")
    assert n == 0


def test_recover_raises_p62_when_kind_unregistered():
    """P62 — kind not in client._replayers ⇒ WALReplayerMissingError."""
    c = InMemoryClient()
    register_replayer(c, "only-this", lambda p: None)
    c.script([
        {"op_id": "op1", "kind": "MISSING", "payload_json": "{}",
         "started_at": "2026-01-01T00:00:00"}
    ])
    with pytest.raises(WALReplayerMissingError, match="MISSING"):
        recover(c, "mg-1")
