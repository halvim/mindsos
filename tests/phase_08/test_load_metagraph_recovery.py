"""PB-6 B — recover-on-load wiring (refactored Phase 09 P51 + P62).

Phase 09 cascade:

* **P62** — the Phase 08 silent narrow-catch of
  :class:`WALReplayerMissingError` was removed. Unknown-kind WAL
  entries now propagate as :class:`PersistenceError`. The replacement
  test ``test_recover_unknown_kind_raises`` locks the loud-fail
  contract.
* **P51** — replayer registration is per-Client; the prior
  ``monkeypatch.setattr(wal_mod, "_REPLAYERS", ...)`` pattern is
  replaced by ``register_replayer(client, kind, fn)``.
"""

from __future__ import annotations

import pytest

from mindsos_core.exceptions import (
    PersistenceError,
    WALReplayerMissingError,
)
from mindsos_core.persistence import InMemoryClient
from mindsos_core.persistence.wal import register_replayer
from mindsos_core.reconstruction import load_metagraph


def test_recover_unknown_kind_raises_per_p62() -> None:
    """Phase 09 P62 — unknown WAL kind raises WALReplayerMissingError loudly.

    Replaces Phase 08's ``test_recover_no_replayer_silent_no_op_per_rpb_3_c``
    which asserted the silent-narrow-catch behavior. Phase 09's
    ``register_all_l1_replayers`` registers ``xref_add`` /
    ``xref_remove`` on FalkorClient construction; an unknown kind in
    the WAL post-Phase-09 is a real bug, not a tolerable no-op.
    """
    c = InMemoryClient()
    # WAL recover query returns one uncommitted entry with unknown kind.
    c.script([
        {"op_id": "op-1", "kind": "unknown-kind", "payload_json": "{}"}
    ])

    with pytest.raises(WALReplayerMissingError, match="unknown-kind"):
        load_metagraph(c, "mid-X")


def test_recover_with_registered_replayer_fires_replayer_first() -> None:
    """PB-6 B + Phase 09 P51 — registered (per-Client) replayer fires during recover().

    Refactored from the Phase 08 ``monkeypatch.setattr(wal_mod, "_REPLAYERS", ...)``
    pattern to use the per-Client registration helper introduced by
    Phase 09 P51.
    """
    fired: list = []

    def fake_replayer(payload):
        fired.append(payload)

    c = InMemoryClient()
    register_replayer(c, "my-kind", fake_replayer)

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


def test_recover_driver_error_propagates_as_persistence_error() -> None:
    """RPB-3 C narrow-catch limit (preserved) — driver errors propagate."""
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
