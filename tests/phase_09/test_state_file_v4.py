"""State-file v=4 — RR-7 single-step _v3_to_v4 + RR-12 CURRENT_VERSION bump."""

from __future__ import annotations

import pytest

from mindsos_cli.migrations import metagraph as mg_migrations


def test_current_version_at_phase_baseline():
    """Phase 10 B-10-T3 — Phase 09 RR-12 bumped CURRENT_VERSION to 4; Phase 10
    M11 bumps to 5. Dynamic >= 4 keeps the assertion stable across bumps
    (audit-class feedback_phase_baseline_literal_audit.md).
    """
    assert mg_migrations.CURRENT_VERSION >= 4


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


def test_migration_chain_v1_through_current():
    """Phase 10 B-10-T3 — chain runs v=1 → CURRENT, picking up every step's
    defaults including the Phase 09 xrefs[] introduction.
    """
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
    assert result["_state_version"] == mg_migrations.CURRENT_VERSION
    # All defaults present.
    assert result["intergraph_edges"] == []
    assert result["schema_name"] is None
    assert result["intergraph_hyperedges"] == []
    assert result["xrefs"] == []


def test_migration_v3_to_current_adds_xrefs():
    """Phase 10 B-10-T3 — v=3 → CURRENT adds xrefs (Phase 09 step). Phase 10's
    additional v=4 → v=5 step adds soft-delete defaults to xref rows.
    """
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
    assert result["_state_version"] == mg_migrations.CURRENT_VERSION
    assert result["xrefs"] == []
    # Pre-existing intergraph_hyperedges preserved.
    assert result["intergraph_hyperedges"] == [{"edge_id": "ihe1"}]


def test_v5_forward_refused():
    forward = mg_migrations.CURRENT_VERSION + 1
    with pytest.raises(ValueError, match=f"v{mg_migrations.CURRENT_VERSION}"):
        mg_migrations.migrate({"_state_version": forward, "name": "test"})


def test_idempotent_at_current():
    """Phase 10 B-10-T3 — input at CURRENT_VERSION migrates to CURRENT_VERSION."""
    state_at_current = {
        "_state_version": mg_migrations.CURRENT_VERSION,
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
    result = mg_migrations.migrate(dict(state_at_current))
    assert result["_state_version"] == mg_migrations.CURRENT_VERSION
    # xref_id preserved; Phase 10 v=5 adds default target_stale/deprecated_at.
    assert result["xrefs"][0]["xref_id"] == "carry"
