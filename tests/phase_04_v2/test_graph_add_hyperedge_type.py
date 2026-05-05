"""Phase 04-v2 — `mindsos graph add-hyperedge --type T` enforcement + schema check."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _setup_schema_with_hyperedge_type(_isolated_state_dir):
    runner.invoke(app, ["schema", "create", "--name", "s1", "--strict"])
    runner.invoke(
        app,
        ["schema", "add-node-type", "--schema", "s1", "--type-name", "Person"],
    )
    runner.invoke(
        app,
        ["schema", "add-node-type", "--schema", "s1", "--type-name", "School"],
    )
    runner.invoke(
        app,
        ["schema", "add-hyperedge-type", "--schema", "s1", "--type-name", "ATTENDS",
         "--allowed-member", "Person", "--allowed-member", "School"],
    )


def test_add_hyperedge_under_strict_schema_member_type_check(_isolated_state_dir):
    """Under strict schema with attached HyperEdgeType, member types validated."""
    _setup_schema_with_hyperedge_type(_isolated_state_dir)
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    runner.invoke(
        app,
        ["graph", "add-node", "Alice", "--name", "g1", "--type", "Person",
         "--node-id", "a"],
    )
    runner.invoke(
        app,
        ["graph", "add-node", "Acme", "--name", "g1", "--type", "School",
         "--node-id", "b"],
    )
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "ATTENDS",
         "--member", "a", "--member", "b", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["type_name"] == "ATTENDS"


def test_add_hyperedge_unknown_type_under_schema_exits_1(_isolated_state_dir):
    """Type not in schema → UnknownTypeError."""
    _setup_schema_with_hyperedge_type(_isolated_state_dir)
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    runner.invoke(
        app,
        ["graph", "add-node", "Alice", "--name", "g1", "--type", "Person",
         "--node-id", "a"],
    )
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "UNKNOWN",
         "--member", "a"],
    )
    assert res.exit_code == 1
    assert "UnknownTypeError" in (res.output + (res.stderr or ""))


def test_add_hyperedge_member_type_mismatch_exits_1(_isolated_state_dir):
    """Member node type not in HyperEdgeType.allowed_member_types → UnknownTypeError."""
    _setup_schema_with_hyperedge_type(_isolated_state_dir)
    runner.invoke(
        app,
        ["schema", "add-node-type", "--schema", "s1", "--type-name", "Cat"],
    )
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    runner.invoke(
        app,
        ["graph", "add-node", "Whiskers", "--name", "g1", "--type", "Cat",
         "--node-id", "c"],
    )
    runner.invoke(
        app,
        ["graph", "add-node", "Acme", "--name", "g1", "--type", "School",
         "--node-id", "b"],
    )
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "ATTENDS",
         "--member", "c", "--member", "b"],
    )
    assert res.exit_code == 1
    assert "UnknownTypeError" in (res.output + (res.stderr or ""))
