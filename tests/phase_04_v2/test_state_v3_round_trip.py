"""Phase 04-v2 — graph state-file v=3 round-trip."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli import state as state_mod
from mindsos_cli.app import app


runner = CliRunner()


def test_v3_hyperedge_carries_type_name(_isolated_state_dir):
    """Phase 04-v2 — hyperedge entry includes `type_name`."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    for nid in ("a", "b"):
        runner.invoke(
            app,
            ["graph", "add-node", nid, "--name", "g1", "--type", "T",
             "--node-id", nid],
        )
    runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "PAIR",
         "--member", "a", "--member", "b"],
    )
    raw = json.loads((_isolated_state_dir / "graph-g1.json").read_text())
    # Phase 05a — current GRAPH_STATE_VERSION is 4 (was 3 in 04-v2).
    # Hyperedges still carry type_name (Phase 04-v2 surface preserved).
    assert raw["_state_version"] == state_mod.GRAPH_STATE_VERSION
    assert raw["hyperedges"][0]["type_name"] == "PAIR"


def test_v3_member_ids_canonically_sorted(_isolated_state_dir):
    """Byte-stable JSON: hyperedge member_ids sorted by node_id."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    for nid in ("c", "a", "b"):
        runner.invoke(
            app,
            ["graph", "add-node", nid, "--name", "g1", "--type", "T",
             "--node-id", nid],
        )
    runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "TRIO",
         "--member", "c", "--member", "a", "--member", "b"],
    )
    raw = json.loads((_isolated_state_dir / "graph-g1.json").read_text())
    assert raw["hyperedges"][0]["member_ids"] == ["a", "b", "c"]


def test_v3_hyperedges_sorted_by_edge_id(_isolated_state_dir):
    """Top-level hyperedges list byte-stable sorted."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(
        app,
        ["graph", "add-node", "a", "--name", "g1", "--type", "T", "--node-id", "a"],
    )
    runner.invoke(
        app,
        ["graph", "add-node", "b", "--name", "g1", "--type", "T", "--node-id", "b"],
    )
    runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "X",
         "--member", "a", "--hyperedge-id", "z-id"],
    )
    runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "Y",
         "--member", "a", "--member", "b", "--hyperedge-id", "a-id"],
    )
    raw = json.loads((_isolated_state_dir / "graph-g1.json").read_text())
    edge_ids = [h["edge_id"] for h in raw["hyperedges"]]
    assert edge_ids == ["a-id", "z-id"]
