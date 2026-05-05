"""Phase 05a — `mindsos metagraph add-graph` (Q5-A + N7-A + P16 + P18)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _create_metagraph_and_graph(name_mg: str, name_g: str) -> None:
    runner.invoke(app, ["metagraph", "create", "--name", name_mg])
    runner.invoke(app, ["graph", "create", "--name", name_g])


def test_add_graph_happy_path(_isolated_state_dir):
    """Add a fresh standalone graph to a metagraph."""
    _create_metagraph_and_graph("mg", "g1")
    res = runner.invoke(
        app,
        ["metagraph", "add-graph", "--name", "mg", "--graph", "g1", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["metagraph"] == "mg"
    assert data["graph"] == "g1"
    assert data["contained_graphs_count"] == 1


def test_add_graph_writes_back_pointer_to_graph_state_file(_isolated_state_dir):
    """P18 — graph state file written FIRST with metagraph_name back-pointer."""
    _create_metagraph_and_graph("mg", "g1")
    runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", "g1"])
    raw = json.loads(
        (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    )
    assert raw["metagraph_name"] == "mg"


def test_add_graph_writes_metagraph_state_file_with_contained_graph(
    _isolated_state_dir,
):
    """Metagraph state file lists the contained graph by name."""
    _create_metagraph_and_graph("mg", "g1")
    runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", "g1"])
    raw = json.loads(
        (_isolated_state_dir / "metagraph-mg.json").read_text(encoding="utf-8")
    )
    assert raw["contained_graphs"] == ["g1"]


def test_add_graph_refuses_already_owned_N7_A(_isolated_state_dir):
    """N7-A — refuses if graph already has metagraph_name back-pointer."""
    _create_metagraph_and_graph("mg-a", "g1")
    runner.invoke(app, ["metagraph", "create", "--name", "mg-b"])
    runner.invoke(app, ["metagraph", "add-graph", "--name", "mg-a", "--graph", "g1"])
    # Now try to add to mg-b.
    res = runner.invoke(
        app,
        ["metagraph", "add-graph", "--name", "mg-b", "--graph", "g1"],
    )
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "already owned by metagraph" in output


def test_add_graph_id_collision_check_Q5_A(_isolated_state_dir):
    """Q5-A — id collision when merging registries refused atomically."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(
        app,
        ["graph", "add-node", "alice", "--name", "g1",
         "--type", "T", "--node-id", "shared-node-id"],
    )
    runner.invoke(app, ["graph", "create", "--name", "g2"])
    runner.invoke(
        app,
        ["graph", "add-node", "bob", "--name", "g2",
         "--type", "T", "--node-id", "shared-node-id"],
    )
    runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", "g1"])
    # Now g2 shares an id with g1's already-merged registry.
    res = runner.invoke(
        app,
        ["metagraph", "add-graph", "--name", "mg", "--graph", "g2"],
    )
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "collision" in output.lower() or "IdentityError" in output


def test_add_graph_multiple_graphs_round_trip(_isolated_state_dir):
    """Multiple graphs in one metagraph survive load + re-save."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    for n in ["alpha", "bravo", "charlie"]:
        runner.invoke(app, ["graph", "create", "--name", n])
        runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", n])
    res = runner.invoke(app, ["metagraph", "inspect", "--name", "mg", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["counts"]["graphs"] == 3
    assert data["contained_graphs"] == ["alpha", "bravo", "charlie"]
