"""Tests for ``mindsos schema inspect``."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_inspect_empty_schema(_isolated_state_dir):
    runner.invoke(app, ["schema", "create", "--name", "s1"])
    res = runner.invoke(app, ["schema", "inspect", "--name", "s1", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["name"] == "s1"
    assert data["strict"] is False
    assert data["node_types"] == []
    assert data["edge_types"] == []


def test_inspect_after_adds(_isolated_state_dir):
    runner.invoke(app, ["schema", "create", "--name", "s1", "--strict"])
    runner.invoke(
        app,
        [
            "schema",
            "add-node-type",
            "--schema",
            "s1",
            "--type-name",
            "Person",
            "--prop-type",
            "age=int",
        ],
    )
    runner.invoke(
        app,
        [
            "schema",
            "add-node-type",
            "--schema",
            "s1",
            "--type-name",
            "Org",
        ],
    )
    runner.invoke(
        app,
        [
            "schema",
            "add-edge-type",
            "--schema",
            "s1",
            "--type-name",
            "WORKS_AT",
            "--allowed-source",
            "Person",
            "--allowed-target",
            "Org",
        ],
    )
    res = runner.invoke(app, ["schema", "inspect", "--name", "s1", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["strict"] is True
    nt_names = [nt["name"] for nt in data["node_types"]]
    assert nt_names == ["Org", "Person"]  # sorted
    assert data["edge_types"][0]["allowed_sources"] == ["Person"]


def test_inspect_missing_exits_1(_isolated_state_dir):
    res = runner.invoke(app, ["schema", "inspect", "--name", "ghost"])
    assert res.exit_code == 1
