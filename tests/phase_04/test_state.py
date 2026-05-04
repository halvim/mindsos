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
    state = {
        "_state_version": 1,
        "name": "s1",
        "strict": True,
        "node_types": [],
        "edge_types": [],
    }
    state_mod.save_schema_state("s1", state)
    loaded = state_mod.load_schema_state("s1")
    assert loaded == state


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
    """Phase 04: graph state file v1 may carry optional schema_name."""
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
    assert loaded == state


def test_graph_state_file_v1_legacy_phase_03_loads(_isolated_state_dir):
    """Phase 04: a Phase 03 graph state file (no schema_name field) loads."""
    legacy = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-000000000002",
        "name": "g",
        "role": "ontology",
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    (_isolated_state_dir / "graph-g.json").write_text(
        json.dumps(legacy), encoding="utf-8"
    )
    loaded = state_mod.load_graph_state("g")
    assert "schema_name" not in loaded  # caller treats missing as None
    assert loaded["name"] == "g"


def test_graph_state_file_v2_round_trip(_isolated_state_dir):
    """Phase 04: writes and reads v=2 graph state files."""
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
    assert loaded == state
    assert loaded["_state_version"] == 2


def test_graph_state_v3_refused(_isolated_state_dir):
    """Phase 04 max_version=2 refuses v=3 (future-version contract)."""
    future = {
        "_state_version": 3,
        "graph_id": "00000000-0000-4000-8000-000000000004",
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
    """Per-kind version constants (Phase 04 — Pick P1)."""
    assert state_mod.GRAPH_STATE_VERSION == 2
    assert state_mod.SCHEMA_STATE_VERSION == 1
    # Backward-compat alias points at GRAPH_STATE_VERSION.
    assert state_mod.STATE_VERSION == state_mod.GRAPH_STATE_VERSION
