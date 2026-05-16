"""M11 + RR-7 — state-file v=4 → v=5 migration (metagraph + graph)."""

from __future__ import annotations

from mindsos_cli import state as state_mod
from mindsos_cli.migrations import graph as g_mig, metagraph as mg_mig


def test_current_versions_bumped_to_5() -> None:
    assert mg_mig.CURRENT_VERSION == 5
    assert g_mig.CURRENT_VERSION == 5
    assert state_mod.METAGRAPH_STATE_VERSION == 5
    assert state_mod.GRAPH_STATE_VERSION == 5


def test_metagraph_v4_to_v5_defaults() -> None:
    state = {
        "_state_version": 4,
        "metaedges": [{"edge_id": "m1"}],
        "metahyperedges": [{"edge_id": "mh1"}],
        "xrefs": [{"xref_id": "x1"}],
    }
    v5 = mg_mig._v4_to_v5(state)
    assert v5["metaedges"][0]["deprecated_at"] is None
    assert v5["metaedges"][0]["disputed_at"] is None
    assert v5["metahyperedges"][0]["deprecated_at"] is None
    assert v5["metahyperedges"][0]["disputed_at"] is None
    assert v5["xrefs"][0]["target_stale"] is False
    assert v5["xrefs"][0]["deprecated_at"] is None


def test_graph_v4_to_v5_defaults() -> None:
    state = {
        "_state_version": 4,
        "edges": [{"edge_id": "e1"}],
        "hyperedges": [{"edge_id": "h1"}],
    }
    v5 = g_mig._v4_to_v5(state)
    assert v5["edges"][0]["deprecated_at"] is None
    assert v5["edges"][0]["disputed_at"] is None
    assert v5["hyperedges"][0]["deprecated_at"] is None
    assert v5["hyperedges"][0]["disputed_at"] is None


def test_migration_idempotent_preserves_existing_values() -> None:
    state = {
        "_state_version": 5,
        "metaedges": [{"edge_id": "m1", "deprecated_at": "2026-05-15T12:00:00+00:00"}],
        "metahyperedges": [],
        "xrefs": [{"xref_id": "x1", "target_stale": True}],
    }
    out = mg_mig._v4_to_v5(state)
    assert out["metaedges"][0]["deprecated_at"] == "2026-05-15T12:00:00+00:00"
    assert out["xrefs"][0]["target_stale"] is True


def test_full_chain_v1_to_v5_metagraph() -> None:
    state = {
        "_state_version": 1,
        "metagraph_id": "mg1",
        "name": "m",
        "properties": {},
        "contained_graphs": [],
        "metaedges": [],
        "metahyperedges": [],
    }
    result = mg_mig.migrate(state)
    assert result["_state_version"] == 5
    assert {"intergraph_edges", "intergraph_hyperedges", "xrefs", "schema_name"} <= set(result)
