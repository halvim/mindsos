"""Phase 05a — Q4-B mutation-refuse on `mindsos graph` for metagraph-owned graphs."""

from __future__ import annotations

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _setup_owned_graph():
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", "g1"])


def test_add_node_refused_on_metagraph_owned(_isolated_state_dir):
    """Q4-B + P2 — add-node refused; stderr suggests metagraph subapp."""
    _setup_owned_graph()
    res = runner.invoke(
        app,
        ["graph", "add-node", "alice", "--name", "g1", "--type", "T"],
    )
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "owned by metagraph 'mg'" in output
    # P2 — stderr suggestion present.
    assert "mindsos metagraph" in output or "detach-metagraph" in output


def test_add_edge_refused_on_metagraph_owned(_isolated_state_dir):
    """Q4-B — add-edge refused."""
    _setup_owned_graph()
    res = runner.invoke(
        app,
        ["graph", "add-edge", "--name", "g1",
         "--source", "x", "--target", "y", "--type", "REL"],
    )
    assert res.exit_code == 1


def test_set_prop_refused_on_metagraph_owned(_isolated_state_dir):
    """Q4-B — set-prop refused."""
    _setup_owned_graph()
    res = runner.invoke(
        app,
        ["graph", "set-prop", "--name", "g1",
         "--node-id", "x", "--prop", "k=v"],
    )
    assert res.exit_code == 1


def test_attach_schema_refused_on_metagraph_owned(_isolated_state_dir):
    """Q4-B — attach-schema refused (defer to Phase 14 for metagraph schema)."""
    _setup_owned_graph()
    runner.invoke(app, ["schema", "create", "--name", "s1"])
    res = runner.invoke(
        app,
        ["graph", "attach-schema", "--name", "g1", "--schema", "s1"],
    )
    assert res.exit_code == 1


def test_reset_refused_on_metagraph_owned(_isolated_state_dir):
    """Q4-B — graph reset refused; routes to metagraph remove-graph."""
    _setup_owned_graph()
    res = runner.invoke(
        app,
        ["graph", "reset", "--name", "g1"],
    )
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "metagraph remove-graph" in output or "owned by metagraph" in output
