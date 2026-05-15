"""State-file v=4 — RR-7 single-step _v3_to_v4 + RR-12 CURRENT_VERSION bump."""

from __future__ import annotations

import pytest

from mindsos_cli.migrations import metagraph as mg_migrations


def test_current_version_is_4():
    """RR-12 — Phase 09 bumps CURRENT_VERSION to 4."""
    assert mg_migrations.CURRENT_VERSION == 4


def test_v3_to_v4_adds_default_xrefs_array():
    """RR-7 — single-step migration adds xrefs[] default."""
    v3 = {"_state_version": 3}
    result = mg_migrations._v3_to_v4(dict(v3))
    assert result["xrefs"] == []


def test_v3_to_v4_preserves_existing_xrefs_field():
    """Idempotent — existing xrefs[] survives migration."""
    v3 = {"_state_version": 3, "xrefs": [{"xref_id": "x1"}]}
    result = mg_migrations._v3_to_v4(dict(v3))
    assert result["xrefs"] == [{"xref_id": "x1"}]


def test_migration_chain_v1_through_v4():
    """v=1 input migrates to v=4 picking up all defaults along the chain."""
    v1 = {
        "_state_version": 1,
        "metagraph_id": "mg-1",
        "name": "m",
        "properties": {},
        "contained_graphs": [],
        "metaedges": [],
        "metahyperedges": [],
    }
    result = mg_migrations.migrate(v1)
    assert result["_state_version"] == 4
    # All defaults present.
    assert result["intergraph_edges"] == []
    assert result["schema_name"] is None
    assert result["intergraph_hyperedges"] == []
    assert result["xrefs"] == []


def test_migration_v3_to_v4_adds_xrefs_only():
    v3 = {
        "_state_version": 3,
        "metagraph_id": "mg-1",
        "name": "m",
        "properties": {},
        "schema_name": None,
        "contained_graphs": [],
        "metaedges": [],
        "metahyperedges": [],
        "intergraph_edges": [],
        "intergraph_hyperedges": [{"edge_id": "ihe1"}],
    }
    result = mg_migrations.migrate(v3)
    assert result["_state_version"] == 4
    assert result["xrefs"] == []
    # Pre-existing intergraph_hyperedges preserved.
    assert result["intergraph_hyperedges"] == [{"edge_id": "ihe1"}]


def test_v5_forward_refused():
    forward = mg_migrations.CURRENT_VERSION + 1
    with pytest.raises(ValueError, match=f"v{mg_migrations.CURRENT_VERSION}"):
        mg_migrations.migrate({"_state_version": forward, "name": "test"})


def test_idempotent_at_v4():
    v4 = {
        "_state_version": 4,
        "metagraph_id": "mg-1",
        "name": "m",
        "properties": {},
        "schema_name": None,
        "contained_graphs": [],
        "metaedges": [],
        "metahyperedges": [],
        "intergraph_edges": [],
        "intergraph_hyperedges": [],
        "xrefs": [{"xref_id": "carry"}],
    }
    result = mg_migrations.migrate(dict(v4))
    assert result["_state_version"] == 4
    assert result["xrefs"] == [{"xref_id": "carry"}]
