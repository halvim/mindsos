"""Test for ``mindsos graph list`` discovery subcommand."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_list_empty(_isolated_state_dir):
    res = runner.invoke(app, ["graph", "list", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["graphs"] == []


def test_list_after_create(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "zebra", "--role", "z"])
    runner.invoke(app, ["graph", "create", "--name", "alpha", "--role", "a"])
    res = runner.invoke(app, ["graph", "list", "--json"])
    data = json.loads(res.output)
    names = [g["name"] for g in data["graphs"]]
    assert names == ["alpha", "zebra"]  # sorted by name (state file alphabetical)
