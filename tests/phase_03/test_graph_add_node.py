"""Tests for ``mindsos graph add-node``."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _create(name="g1"):
    runner.invoke(app, ["graph", "create", "--name", name])


def test_add_node_happy_path(_isolated_state_dir):
    _create()
    res = runner.invoke(
        app,
        ["graph", "add-node", "Alice", "--name", "g1", "--type", "Person", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["value"] == "Alice"
    assert data["type_name"] == "Person"


def test_add_node_explicit_node_id(_isolated_state_dir):
    _create()
    res = runner.invoke(
        app,
        [
            "graph", "add-node", "x", "--name", "g1", "--type", "T",
            "--node-id", "iri:my-node", "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["node_id"] == "iri:my-node"


def test_add_node_duplicate_id_exits_1(_isolated_state_dir):
    _create()
    runner.invoke(
        app,
        ["graph", "add-node", "x", "--name", "g1", "--type", "T",
         "--node-id", "dup"],
    )
    res = runner.invoke(
        app,
        ["graph", "add-node", "y", "--name", "g1", "--type", "T",
         "--node-id", "dup"],
    )
    assert res.exit_code == 1
    assert "IdentityError" in (res.output + (res.stderr or ""))


def test_add_node_prop_int(_isolated_state_dir):
    _create()
    res = runner.invoke(
        app,
        ["graph", "add-node", "x", "--name", "g1", "--type", "T",
         "--prop", "count=42", "--json"],
    )
    data = json.loads(res.output)
    assert data["properties"]["count"] == 42


def test_add_node_prop_list(_isolated_state_dir):
    _create()
    res = runner.invoke(
        app,
        ["graph", "add-node", "x", "--name", "g1", "--type", "T",
         "--prop", 'tags=["a","b"]', "--json"],
    )
    data = json.loads(res.output)
    assert data["properties"]["tags"] == ["a", "b"]


def test_add_node_prop_bool(_isolated_state_dir):
    _create()
    res = runner.invoke(
        app,
        ["graph", "add-node", "x", "--name", "g1", "--type", "T",
         "--prop", "active=true", "--json"],
    )
    data = json.loads(res.output)
    assert data["properties"]["active"] is True


def test_add_node_prop_string_fallback(_isolated_state_dir):
    _create()
    res = runner.invoke(
        app,
        ["graph", "add-node", "x", "--name", "g1", "--type", "T",
         "--prop", "nick=Alice", "--json"],
    )
    data = json.loads(res.output)
    assert data["properties"]["nick"] == "Alice"


def test_add_node_value_json_int(_isolated_state_dir):
    """<VALUE> follows the same json-then-string rule."""
    _create()
    res = runner.invoke(
        app,
        ["graph", "add-node", "42", "--name", "g1", "--type", "T", "--json"],
    )
    data = json.loads(res.output)
    assert data["value"] == 42


def test_add_node_prop_empty_key_exits_2(_isolated_state_dir):
    _create()
    res = runner.invoke(
        app,
        ["graph", "add-node", "x", "--name", "g1", "--type", "T",
         "--prop", "=value"],
    )
    assert res.exit_code == 2
