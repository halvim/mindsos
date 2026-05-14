"""RPB-6 A — Phase 08 loader does NOT query :MetagraphSettings."""

from __future__ import annotations

from mindsos_core.exceptions import PersistenceError
from mindsos_core.persistence import InMemoryClient
from mindsos_core.reconstruction import load_metagraph


def test_load_metagraph_does_not_emit_metagraph_settings_query() -> None:
    """RPB-6 A — strip v3's `_migrate_legacy_settings`; no MATCH (s:MetagraphSettings)."""
    c = InMemoryClient()
    # WAL recover (empty).
    c.script([])
    # Empty anchor — load fails, but we want to inspect the full call
    # log to confirm NO MetagraphSettings query was emitted.
    c.script([])
    try:
        load_metagraph(c, "mid-X")
    except PersistenceError:
        pass

    for query, _params in c.calls:
        assert "MetagraphSettings" not in query, (
            "Phase 08 loader must not query :MetagraphSettings; "
            "RPB-6 A stripped the v3 migration. Found query: "
            f"{query[:120]!r}"
        )
