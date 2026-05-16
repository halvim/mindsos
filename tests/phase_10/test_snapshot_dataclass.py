"""Snapshot dataclass shape (Phase 10 — ADR-0027 + ADR-0028 + P84 allow-list)."""

from __future__ import annotations

from dataclasses import fields

from mindsos_core import MetagraphSnapshot
from mindsos_core.metagraph_snapshot import _GraphSnap


def test_metagraphsnapshot_field_set() -> None:
    """M3 + P84 — 12 covered attributes + identity ids."""
    expected = {
        "_metagraph_id",
        "_metagraph_props",
        "_graphs",
        "_metaedges",
        "_metahyperedges",
        "_intergraph_edges",         # P84 addition
        "_intergraph_hyperedges",    # P84 addition
        "_schema_name",              # P84 addition
        "_schema",                   # P84 addition
        "_xrefs",
        "_xrefs_dirty",              # RB1 addition
        "_soft_delete_dirty",        # RPB-11 addition
        "_identity_ids",
    }
    actual = {f.name for f in fields(MetagraphSnapshot)}
    assert actual == expected, f"covered fields drift: {actual - expected=} {expected - actual=}"


def test_graph_snap_field_set() -> None:
    """P85 + P86 — _GraphSnap has properties + soft_delete_dirty."""
    expected = {
        "graph_id",
        "name",
        "role",
        "schema",
        "nodes",
        "edges",
        "hyperedges",
        "properties",          # P85
        "soft_delete_dirty",   # P86
    }
    actual = {f.name for f in fields(_GraphSnap)}
    assert actual == expected, f"_GraphSnap field drift: {actual - expected=} {expected - actual=}"
