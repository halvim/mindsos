"""Phase 05a — `mindsos metagraph remove-graph` (P19 always-cascade slim)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _setup_with_metaedges():
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    for n in ["g1", "g2", "g3"]:
        runner.invoke(app, ["graph", "create", "--name", n])
        runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", n])
    runner.invoke(
        app,
        ["metagraph", "add-metaedge", "--name", "mg",
         "--source-graph", "g1", "--target-graph", "g2", "--type", "REL"],
    )
    runner.invoke(
        app,
        ["metagraph", "add-metaedge", "--name", "mg",
         "--source-graph", "g2", "--target-graph", "g3", "--type", "REL"],
    )


def test_remove_graph_cascades_metaedges(_isolated_state_dir):
    """N4-A — slim cascade: incident metaedges removed."""
    _setup_with_metaedges()
    res = runner.invoke(
        app,
        ["metagraph", "remove-graph", "--name", "mg", "--graph", "g2", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["cascaded_metaedges"] == 2
    # Metagraph state file: g2 gone; metaedges empty.
    raw = json.loads(
        (_isolated_state_dir / "metagraph-mg.json").read_text(encoding="utf-8")
    )
    assert "g2" not in raw["contained_graphs"]
    assert raw["metaedges"] == []


def test_remove_graph_clears_back_pointer_on_removed_graph(_isolated_state_dir):
    """Removed graph's metagraph_name back-pointer is cleared."""
    _setup_with_metaedges()
    runner.invoke(app, ["metagraph", "remove-graph", "--name", "mg", "--graph", "g1"])
    raw = json.loads(
        (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    )
    assert raw["metagraph_name"] is None


def test_remove_graph_unknown_graph(_isolated_state_dir):
    """Removing a graph not in the metagraph raises IdentityError → exit 1."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    res = runner.invoke(
        app,
        ["metagraph", "remove-graph", "--name", "mg", "--graph", "no-such"],
    )
    assert res.exit_code == 1
