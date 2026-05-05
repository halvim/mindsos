"""Phase 05a — Graph state-file v=4 (B2 back-pointer + cumulative migration)."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from mindsos_cli import state as state_mod
from mindsos_cli.app import app


runner = CliRunner()


def test_v4_back_pointer_round_trip(_isolated_state_dir):
    """B2 — metagraph_name back-pointer field round-trips through state file."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", "g1"])
    raw = json.loads(
        (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    )
    assert raw["_state_version"] == state_mod.GRAPH_STATE_VERSION  # = 4
    assert raw["metagraph_name"] == "mg"


def test_cumulative_migration_v1_to_v4(_isolated_state_dir):
    """Loading a Phase 03 v=1 file forward-migrates to v=4 in memory."""
    legacy_v1 = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-00000000a001",
        "name": "g1",
        "role": None,
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    (_isolated_state_dir / "graph-g1.json").write_text(
        json.dumps(legacy_v1), encoding="utf-8"
    )
    loaded = state_mod.load_graph_state("g1")
    assert loaded["_state_version"] == 4
    assert loaded["schema_name"] is None     # v=1 → v=2 default.
    assert loaded["metagraph_name"] is None  # v=3 → v=4 default.


def test_cumulative_migration_v3_to_v4(_isolated_state_dir):
    """Loading a Phase 04-v2 v=3 file forward-migrates to v=4."""
    legacy_v3 = {
        "_state_version": 3,
        "graph_id": "00000000-0000-4000-8000-00000000a002",
        "name": "g2",
        "role": "ontology",
        "schema_name": "s1",
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    (_isolated_state_dir / "graph-g2.json").write_text(
        json.dumps(legacy_v3), encoding="utf-8"
    )
    loaded = state_mod.load_graph_state("g2")
    assert loaded["_state_version"] == 4
    assert loaded["metagraph_name"] is None


def test_v5_future_version_refused(_isolated_state_dir):
    """Forward-version (v=5) refused with strict-version contract."""
    future = {
        "_state_version": 5,
        "graph_id": "00000000-0000-4000-8000-00000000a003",
        "name": "g3",
        "role": None,
        "nodes": [], "edges": [], "hyperedges": [],
    }
    (_isolated_state_dir / "graph-g3.json").write_text(
        json.dumps(future), encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="this CLI supports v4"):
        state_mod.load_graph_state("g3")
