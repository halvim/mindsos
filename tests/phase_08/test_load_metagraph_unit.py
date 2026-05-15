"""Unit assertions for the MetagraphLoader locked load sequence (R4-1 A + M12)."""

from __future__ import annotations

import pytest

from mindsos_core.exceptions import PersistenceError
from mindsos_core.persistence import InMemoryClient
from mindsos_core.reconstruction import load_metagraph


def test_anchor_missing_raises_persistence_error() -> None:
    """No :Metagraph row → PersistenceError."""
    c = InMemoryClient()
    c.script([])  # WAL recover — no replayers, empty result.
    c.script([])  # Anchor MATCH returns empty.
    with pytest.raises(PersistenceError, match="No :Metagraph row"):
        load_metagraph(c, "ghost-mid")


def test_recover_fires_before_any_read_query() -> None:
    """R4-8 A / PB-6 B — recover() runs FIRST.

    Inspecting the InMemoryClient call log, the FIRST query is a WAL
    select (recover's read of uncommitted entries), and the SECOND is
    the :Metagraph anchor MATCH.
    """
    c = InMemoryClient()
    # WAL recover query — return empty so recover() no-ops.
    c.script([])
    # Anchor MATCH — return empty (we just want to capture the call
    # order; the load can fail after).
    c.script([])
    try:
        load_metagraph(c, "ghost-mid")
    except PersistenceError:
        pass

    # WAL recover query happens BEFORE the :Metagraph anchor MATCH.
    assert len(c.calls) >= 2
    wal_query, _wal_params = c.calls[0]
    anchor_query, _anchor_params = c.calls[1]
    assert "WALEntry" in wal_query or "committed" in wal_query
    assert "MATCH (m:Metagraph {id:" in anchor_query


def test_load_metagraph_emits_anchor_with_schema_name_property() -> None:
    """Anchor read query includes ``schema_name`` (PB-11 A)."""
    c = InMemoryClient()
    c.script([])  # WAL recover.
    c.script([])  # Empty anchor MATCH.
    try:
        load_metagraph(c, "mid-X")
    except PersistenceError:
        pass

    anchor_call = c.calls[1]
    query, _params = anchor_call
    assert "schema_name" in query
    assert "_props_json" in query
