"""Tests for ``mindsos graph inspect``."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_inspect_empty_graph(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    res = runner.invoke(app, ["graph", "inspect", "--name", "g1", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["counts"] == {"nodes": 0, "edges": 0, "hyperedges": 0}


def test_inspect_after_add_node(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(
        app,
        ["graph", "add-node", "Alice", "--name", "g1", "--type", "Person"],
    )
    res = runner.invoke(app, ["graph", "inspect", "--name", "g1", "--json"])
    data = json.loads(res.output)
    assert data["counts"]["nodes"] == 1


def test_inspect_missing_graph_exits_1(_isolated_state_dir):
    res = runner.invoke(app, ["graph", "inspect", "--name", "missing"])
    assert res.exit_code == 1
