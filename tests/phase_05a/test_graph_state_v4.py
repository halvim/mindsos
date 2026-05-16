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


def test_cumulative_migration_v1_to_current(_isolated_state_dir):
    """Loading a Phase 03 v=1 file forward-migrates to CURRENT_VERSION in memory.

    Phase 10 B-10-T3 — Phase 05a baseline literal ``== 4`` patched to
    dynamic ``state_mod.GRAPH_STATE_VERSION`` per the B-09-T3 audit class
    (feedback_phase_baseline_literal_audit.md).
    """
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
    assert loaded["_state_version"] == state_mod.GRAPH_STATE_VERSION
    assert loaded["schema_name"] is None     # v=1 → v=2 default.
    assert loaded["metagraph_name"] is None  # v=3 → v=4 default.


def test_cumulative_migration_v3_to_current(_isolated_state_dir):
    """Loading a Phase 04-v2 v=3 file forward-migrates to CURRENT_VERSION."""
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
    assert loaded["_state_version"] == state_mod.GRAPH_STATE_VERSION
    assert loaded["metagraph_name"] is None


def test_future_version_refused(_isolated_state_dir):
    """Forward-version (CURRENT_VERSION + 1) refused with strict-version contract.

    Phase 10 B-10-T3 — Phase 05a wrote this test against v=5 (then-future).
    Phase 10 bumps to v=5 → v=5 is now CURRENT, no longer refused. Use
    CURRENT+1 dynamically so the test stays valid through future bumps.
    """
    future_v = state_mod.GRAPH_STATE_VERSION + 1
    future = {
        "_state_version": future_v,
        "graph_id": "00000000-0000-4000-8000-00000000a003",
        "name": "g3",
        "role": None,
        "nodes": [], "edges": [], "hyperedges": [],
    }
    (_isolated_state_dir / "graph-g3.json").write_text(
        json.dumps(future), encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match=f"this CLI supports v{state_mod.GRAPH_STATE_VERSION}"):
        state_mod.load_graph_state("g3")
