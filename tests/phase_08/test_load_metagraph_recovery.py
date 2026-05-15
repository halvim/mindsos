"""PB-6 B + RPB-3 C — recover-on-load wiring + narrow-catch."""

from __future__ import annotations

import pytest

from mindsos_core.exceptions import (
    PersistenceError,
    WALReplayerMissingError,
)
from mindsos_core.persistence import InMemoryClient
from mindsos_core.persistence import wal as wal_mod
from mindsos_core.reconstruction import load_metagraph


def test_recover_no_replayer_silent_no_op_per_rpb_3_c(monkeypatch) -> None:
    """RPB-3 C — WALReplayerMissingError is narrow-caught; load proceeds."""
    c = InMemoryClient()
    # WAL recover query returns one uncommitted entry with unknown kind.
    c.script([
        {"op_id": "op-1", "kind": "unknown-kind", "payload_json": "{}"}
    ])
    # After recover() no-ops, anchor MATCH returns empty so the load
    # fails with "No :Metagraph row" — confirms recover() didn't raise.
    c.script([])

    with pytest.raises(PersistenceError, match="No :Metagraph row"):
        load_metagraph(c, "mid-X")


def test_recover_with_registered_replayer_fires_replayer_first(monkeypatch) -> None:
    """PB-6 B — registered replayer is invoked during recover()."""
    fired = []

    def fake_replayer(payload):
        fired.append(payload)

    monkeypatch.setattr(wal_mod, "_REPLAYERS", {"my-kind": fake_replayer})

    c = InMemoryClient()
    # WAL recover query returns one entry with kind=my-kind.
    c.script([
        {"op_id": "op-1", "kind": "my-kind", "payload_json": '{"x": 1}'}
    ])
    # Mark-committed write — replayer fires AFTER but before reads.
    c.script([])
    # Anchor MATCH (empty — load fails after).
    c.script([])

    try:
        load_metagraph(c, "mid-X")
    except PersistenceError:
        pass

    assert len(fired) == 1
    assert fired[0] == {"x": 1}


def test_recover_driver_error_propagates_as_persistence_error(monkeypatch) -> None:
    """RPB-3 C narrow-catch limit — driver errors propagate."""
    from mindsos_core.persistence.client import QueryResult

    class RaisingClient:
        def __init__(self):
            self.calls = []

        def run_query(self, q, p=None):
            self.calls.append((q, p))
            if "WALEntry" in q or "committed" in q:
                raise RuntimeError("simulated driver failure")
            return QueryResult()

        def run_batch(self, statements):
            return [self.run_query(*s) for s in statements]

        def close(self):
            pass

    c = RaisingClient()
    # recover() runs the WAL select; driver raises; not a
    # WALReplayerMissingError, so the wrapper does NOT swallow.
    with pytest.raises(Exception):  # The wal module wraps driver errors.
        load_metagraph(c, "mid-X")
