"""Direct unit tests for ``mindsos_cli.state`` schema-file helpers (Phase 04)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mindsos_cli import state as state_mod


def test_schema_file_path_uses_state_dir(_isolated_state_dir):
    path = state_mod.schema_file_path("alpha")
    assert path == _isolated_state_dir / "schema-alpha.json"


def test_schema_file_path_rejects_invalid_name(_isolated_state_dir):
    with pytest.raises(ValueError):
        state_mod.schema_file_path("foo/bar")


def test_save_then_load_schema_state_round_trip(_isolated_state_dir):
    """Phase 05a — migration chain forward-fills v=1 schema → current."""
    state = {
        "_state_version": 1,
        "name": "s1",
        "strict": True,
        "node_types": [],
        "edge_types": [],
    }
    state_mod.save_schema_state("s1", state)
    loaded = state_mod.load_schema_state("s1")
    assert loaded["_state_version"] == state_mod.SCHEMA_STATE_VERSION
    assert loaded["name"] == "s1"
    assert loaded["strict"] is True
    # P04-v2 default: missing hyperedge_types treated as empty list.
    assert loaded["hyperedge_types"] == []


def test_save_schema_state_is_atomic(_isolated_state_dir):
    state = {
        "_state_version": 1,
        "name": "s1",
        "strict": False,
        "node_types": [],
        "edge_types": [],
    }
    state_mod.save_schema_state("s1", state)
    # No leftover .tmp file
    assert not (_isolated_state_dir / "schema-s1.json.tmp").exists()
    assert (_isolated_state_dir / "schema-s1.json").exists()


def test_load_schema_state_missing_file_raises(_isolated_state_dir):
    with pytest.raises(FileNotFoundError):
        state_mod.load_schema_state("never-created")


def test_load_schema_state_corrupt_json_raises_runtime(_isolated_state_dir):
    (_isolated_state_dir / "schema-bad.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(RuntimeError):
        state_mod.load_schema_state("bad")


def test_load_schema_state_missing_version_raises(_isolated_state_dir):
    (_isolated_state_dir / "schema-noversion.json").write_text(
        json.dumps({"name": "noversion"}), encoding="utf-8"
    )
    with pytest.raises(RuntimeError):
        state_mod.load_schema_state("noversion")


def test_load_schema_state_future_version_refused(_isolated_state_dir):
    (_isolated_state_dir / "schema-future.json").write_text(
        json.dumps({"_state_version": 99, "name": "future"}), encoding="utf-8"
    )
    with pytest.raises(RuntimeError):
        state_mod.load_schema_state("future")


def test_iter_schema_files_sorted(_isolated_state_dir):
    for n in ["zeta", "alpha", "mu"]:
        state_mod.save_schema_state(
            n,
            {
                "_state_version": 1,
                "name": n,
                "strict": False,
                "node_types": [],
                "edge_types": [],
            },
        )
    files = [p.stem.removeprefix("schema-") for p in state_mod.iter_schema_files()]
    assert files == ["alpha", "mu", "zeta"]


def test_delete_schema_state_file_idempotence(_isolated_state_dir):
    state_mod.save_schema_state(
        "ephemeral",
        {
            "_state_version": 1,
            "name": "ephemeral",
            "strict": False,
            "node_types": [],
            "edge_types": [],
        },
    )
    state_mod.delete_schema_state_file("ephemeral")
    assert not (_isolated_state_dir / "schema-ephemeral.json").exists()
    with pytest.raises(FileNotFoundError):
        state_mod.delete_schema_state_file("ephemeral")


def test_graph_state_file_v1_accepts_optional_schema_name(_isolated_state_dir):
    """Phase 04: graph state file v1 may carry optional schema_name.

    Phase 05a — migration chain forward-migrates on load; loaded dict
    has current _state_version + metagraph_name field added.
    """
    state = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-000000000001",
        "name": "g",
        "role": None,
        "schema_name": None,
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    state_mod.save_graph_state("g", state)
    loaded = state_mod.load_graph_state("g")
    assert loaded["_state_version"] == state_mod.GRAPH_STATE_VERSION
    assert loaded["schema_name"] is None
    assert loaded["metagraph_name"] is None
    assert loaded["graph_id"] == state["graph_id"]


def test_graph_state_file_v1_legacy_phase_03_loads(_isolated_state_dir):
    """Phase 04: a Phase 03 graph state file (no schema_name field) loads.

    Phase 05a — migration chain populates schema_name=None and
    metagraph_name=None defaults; the on-disk file is unchanged until
    the next save.
    """
    legacy = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-000000000002",
        "name": "g",
        "role": "ontology",
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    path = _isolated_state_dir / "graph-g.json"
    path.write_text(json.dumps(legacy), encoding="utf-8")
    loaded = state_mod.load_graph_state("g")
    # Migration chain populates default-None fields.
    assert loaded["schema_name"] is None
    assert loaded["metagraph_name"] is None
    assert loaded["name"] == "g"
    # On-disk file unchanged (load is read-only).
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["_state_version"] == 1
    assert "schema_name" not in raw
    assert "metagraph_name" not in raw


def test_graph_state_file_v2_round_trip(_isolated_state_dir):
    """Phase 04 — Phase 04-v2 still reads + accepts v=2 files (cumulative migration).

    Note: Phase 04-v2 always WRITES v=3, so a save_graph_state call writing
    a v=2 dict literal still loads (max_version=3). This test pins
    backward-compat tolerance.
    """
    state = {
        "_state_version": 2,
        "graph_id": "00000000-0000-4000-8000-000000000003",
        "name": "g",
        "role": "ontology",
        "schema_name": "s1",
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    state_mod.save_graph_state("g", state)
    loaded = state_mod.load_graph_state("g")
    # Phase 05a — migration chain forward-migrates v=2 → current. Loader
    # now returns the migrated dict (with metagraph_name=None default).
    assert loaded["_state_version"] == state_mod.GRAPH_STATE_VERSION
    assert loaded["schema_name"] == "s1"
    assert loaded["metagraph_name"] is None


def test_graph_state_v3_round_trip(_isolated_state_dir):
    """Phase 04-v2 v=3 file loads under Phase 05a (migration chain to v=4)."""
    state = {
        "_state_version": 3,
        "graph_id": "00000000-0000-4000-8000-000000000004",
        "name": "g",
        "role": "ontology",
        "schema_name": "s1",
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    state_mod.save_graph_state("g", state)
    loaded = state_mod.load_graph_state("g")
    # Phase 05a — migration chain forward-migrates v=3 → v=4 (default
    # metagraph_name=None). The on-disk file is unchanged until next save.
    assert loaded["_state_version"] == state_mod.GRAPH_STATE_VERSION
    assert loaded["metagraph_name"] is None


def test_graph_state_future_version_refused(_isolated_state_dir):
    """Forward-version files refused (Phase 05a current = v=4; v=5 not supported)."""
    future = {
        "_state_version": state_mod.GRAPH_STATE_VERSION + 1,
        "graph_id": "00000000-0000-4000-8000-000000000005",
        "name": "g",
        "role": None,
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    (_isolated_state_dir / "graph-g.json").write_text(
        json.dumps(future), encoding="utf-8"
    )
    with pytest.raises(RuntimeError):
        state_mod.load_graph_state("g")


def test_graph_state_version_constants_split(_isolated_state_dir):
    """Per-kind version constants (Phase 04 — Pick P1; Phase 04-v2/05a bumps).

    Pre-implementation audit (PHASE_MAP §5 amendment 21): tests reference
    ``state_mod.GRAPH_STATE_VERSION`` dynamically rather than hard-coding
    the int.
    """
    assert state_mod.GRAPH_STATE_VERSION == 4   # Phase 05a (unchanged in 05b).
    assert state_mod.SCHEMA_STATE_VERSION == 2  # Phase 04-v2 (unchanged in 05a/05b).
    assert state_mod.METAGRAPH_STATE_VERSION == 2  # Phase 05b — bumped from 1 (Pushback 18-A).
    assert state_mod.METAGRAPH_SCHEMA_STATE_VERSION == 1  # Phase 05b — NEW kind.
    # Backward-compat alias points at GRAPH_STATE_VERSION.
    assert state_mod.STATE_VERSION == state_mod.GRAPH_STATE_VERSION
