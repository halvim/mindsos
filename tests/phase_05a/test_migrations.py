"""Phase 05a — migration chain helpers (P12 + P14)."""

from __future__ import annotations

import pytest

from mindsos_cli.migrations import graph as graph_migrations
from mindsos_cli.migrations import metagraph as metagraph_migrations
from mindsos_cli.migrations import schema as schema_migrations


# ── chain composition (graph) ───────────────────────────────────────────────


def test_graph_chain_v1_through_v4_in_one_call():
    """Chain composition: v=1 input migrates through every step to current."""
    state = {
        "_state_version": 1,
        "graph_id": "x",
        "name": "g",
        "role": None,
        "nodes": [{"node_id": "n", "value": "v", "type_name": "T",
                   "properties": {}}],
        "edges": [],
        "hyperedges": [{"edge_id": "e", "member_ids": ["n"],
                        "label": None, "properties": {}}],
    }
    out = graph_migrations.migrate(state)
    assert out["_state_version"] == graph_migrations.CURRENT_VERSION  # = 4
    # v=1 → v=2: schema_name default None.
    assert out["schema_name"] is None
    # v=2 → v=3: hyperedge type_name UNSPECIFIED.
    assert out["hyperedges"][0]["type_name"] == "UNSPECIFIED"
    # v=3 → v=4: metagraph_name default None.
    assert out["metagraph_name"] is None


def test_graph_chain_at_current_is_idempotent():
    """A v=4 input passes through with no changes."""
    state = {
        "_state_version": 4,
        "graph_id": "x",
        "name": "g",
        "role": None,
        "schema_name": None,
        "metagraph_name": None,
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    pre = dict(state)
    out = graph_migrations.migrate(state)
    assert out["_state_version"] == 4
    assert out == pre


def test_graph_chain_rejects_forward_version():
    """v=5 raises ValueError ('this CLI supports v4')."""
    with pytest.raises(ValueError, match="this CLI supports v4"):
        graph_migrations.migrate({"_state_version": 5})


def test_graph_chain_rejects_missing_version():
    """No _state_version field raises ValueError ('missing required field')."""
    with pytest.raises(ValueError, match="missing required field"):
        graph_migrations.migrate({"name": "g"})


# ── chain composition (schema) ──────────────────────────────────────────────


def test_schema_chain_v1_to_v2():
    """v=1 → v=2: hyperedge_types default empty list."""
    state = {
        "_state_version": 1, "name": "s", "strict": False,
        "node_types": [], "edge_types": [],
    }
    out = schema_migrations.migrate(state)
    assert out["_state_version"] == 2
    assert out["hyperedge_types"] == []


def test_schema_chain_at_current_is_idempotent():
    state = {
        "_state_version": 2, "name": "s", "strict": False,
        "node_types": [], "edge_types": [], "hyperedge_types": [],
    }
    out = schema_migrations.migrate(state)
    assert out["_state_version"] == 2


# ── chain composition (metagraph) ───────────────────────────────────────────


def test_metagraph_chain_v1_migrates_to_current():
    """Phase 05b bumped METAGRAPH_STATE_VERSION 1 → 2 (Pushback 18-A);
    a v=1 input is forward-migrated to v=2 with default ``intergraph_edges=[]``
    and ``schema_name=None`` populated.
    """
    state = {
        "_state_version": 1,
        "metagraph_id": "mg-id", "name": "mg", "properties": {},
        "contained_graphs": [],
        "metaedges": [], "metahyperedges": [],
    }
    out = metagraph_migrations.migrate(state)
    assert out["_state_version"] == metagraph_migrations.CURRENT_VERSION  # = 2 in 05b
    # 05b additions populated with defaults.
    assert out["intergraph_edges"] == []
    assert out["schema_name"] is None


def test_metagraph_chain_rejects_forward_version():
    """Forward-version (CURRENT_VERSION + 1) raises ('this CLI supports v...')."""
    forward = metagraph_migrations.CURRENT_VERSION + 1
    with pytest.raises(
        ValueError,
        match=f"this CLI supports v{metagraph_migrations.CURRENT_VERSION}",
    ):
        metagraph_migrations.migrate({"_state_version": forward})
