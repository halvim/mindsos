"""Tests for ``mindsos graph add-edge``."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _setup_two_nodes(_isolated_state_dir, name="g1"):
    runner.invoke(app, ["graph", "create", "--name", name])
    runner.invoke(
        app,
        ["graph", "add-node", "Alice", "--name", name, "--type", "Person",
         "--node-id", "n-a"],
    )
    runner.invoke(
        app,
        ["graph", "add-node", "Acme", "--name", name, "--type", "Org",
         "--node-id", "n-b"],
    )


def test_add_edge_happy_path(_isolated_state_dir):
    _setup_two_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-edge", "--name", "g1", "--source", "n-a",
         "--target", "n-b", "--type", "WORKS_AT", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["source_id"] == "n-a"
    assert data["target_id"] == "n-b"
    assert data["type_name"] == "WORKS_AT"


def test_add_edge_lowercase_rel_type_exits_1(_isolated_state_dir):
    _setup_two_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-edge", "--name", "g1", "--source", "n-a",
         "--target", "n-b", "--type", "works_at"],
    )
    assert res.exit_code == 1
    assert "CypherError" in (res.output + (res.stderr or ""))


def test_add_edge_mixed_case_rel_type_exits_1(_isolated_state_dir):
    _setup_two_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-edge", "--name", "g1", "--source", "n-a",
         "--target", "n-b", "--type", "Works_At"],
    )
    assert res.exit_code == 1


def test_add_edge_missing_source_exits_1(_isolated_state_dir):
    _setup_two_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-edge", "--name", "g1", "--source", "missing",
         "--target", "n-b", "--type", "WORKS_AT"],
    )
    assert res.exit_code == 1
    assert "IdentityError" in (res.output + (res.stderr or ""))


def test_add_edge_explicit_edge_id(_isolated_state_dir):
    _setup_two_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-edge", "--name", "g1", "--source", "n-a",
         "--target", "n-b", "--type", "WORKS_AT",
         "--edge-id", "e-1", "--json"],
    )
    data = json.loads(res.output)
    assert data["edge_id"] == "e-1"
