"""Tests for ``mindsos graph create``."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_create_writes_state_file(_isolated_state_dir):
    res = runner.invoke(app, ["graph", "create", "--name", "g1"])
    assert res.exit_code == 0, res.output
    assert (_isolated_state_dir / "graph-g1.json").exists()


def test_create_json_output_has_graph_id(_isolated_state_dir):
    res = runner.invoke(app, ["graph", "create", "--name", "g1", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["name"] == "g1"
    assert data["role"] is None
    assert "graph_id" in data
    # UUID4 format check
    assert len(data["graph_id"]) == 36


def test_create_with_role(_isolated_state_dir):
    res = runner.invoke(
        app, ["graph", "create", "--name", "g1", "--role", "ontology", "--json"]
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["role"] == "ontology"


def test_create_duplicate_name_exits_1(_isolated_state_dir):
    res1 = runner.invoke(app, ["graph", "create", "--name", "g1"])
    assert res1.exit_code == 0
    res2 = runner.invoke(app, ["graph", "create", "--name", "g1"])
    assert res2.exit_code == 1
    assert "already exists" in res2.output or "already exists" in (res2.stderr or "")


def test_create_invalid_name_exits_2(_isolated_state_dir):
    res = runner.invoke(app, ["graph", "create", "--name", "foo/bar"])
    assert res.exit_code == 2
