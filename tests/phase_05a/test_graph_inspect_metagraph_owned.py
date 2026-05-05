"""Phase 05a — Q4-B warn-and-show on `mindsos graph inspect <metagraph-owned>`."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _setup_owned_graph():
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", "g1"])


def _extract_json(output: str) -> dict:
    """Strip leading stderr-mixed lines; return the JSON dict portion."""
    idx = output.find("{")
    return json.loads(output[idx:])


def test_inspect_metagraph_owned_warns_but_succeeds(_isolated_state_dir):
    """Q4-B — read-side: WARN-and-show; exit 0; output present."""
    _setup_owned_graph()
    res = runner.invoke(
        app,
        ["graph", "inspect", "--name", "g1", "--json"],
    )
    assert res.exit_code == 0, res.output
    # Stderr warning may be mixed in (Q4-B warn-and-show).
    data = _extract_json(res.output)
    assert data["name"] == "g1"
    assert data["metagraph_name"] == "mg"


def test_list_nodes_metagraph_owned_warns_but_succeeds(_isolated_state_dir):
    """Q4-B — list-nodes is a read; warn-and-show."""
    _setup_owned_graph()
    res = runner.invoke(
        app,
        ["graph", "list-nodes", "--name", "g1", "--json"],
    )
    assert res.exit_code == 0, res.output
