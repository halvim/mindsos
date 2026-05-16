"""M8 — wrapper grows 2 → 10 WAL replayer kinds."""

from __future__ import annotations

from mindsos_core.persistence import InMemoryClient
from mindsos_core.persistence.bootstrap import register_all_l1_replayers


EXPECTED_KINDS = {
    # Phase 09 carry (2)
    "xref_add",
    "xref_remove",
    # Phase 10 XRef PX2 (4)
    "xref_mark_stale",
    "xref_unmark_stale",
    "xref_deprecate",
    "xref_undeprecate",
    # Phase 10 collapsed element-side M8 (4)
    "element_deprecate",
    "element_undeprecate",
    "element_dispute",
    "element_undispute",
}


def test_wrapper_registers_10_kinds() -> None:
    client = InMemoryClient()
    register_all_l1_replayers(client)
    assert set(client._replayers.keys()) == EXPECTED_KINDS


def test_wrapper_idempotent() -> None:
    """Calling twice is idempotent (RR-16 per-Client registry semantics)."""
    client = InMemoryClient()
    register_all_l1_replayers(client)
    register_all_l1_replayers(client)
    assert set(client._replayers.keys()) == EXPECTED_KINDS
