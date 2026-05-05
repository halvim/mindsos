"""Phase 04-v2 — `mindsos schema add-hyperedge-type` CLI."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _create_schema_with_node_types(_isolated_state_dir, name="s1"):
    runner.invoke(app, ["schema", "create", "--name", name])
    runner.invoke(
        app, ["schema", "add-node-type", "--schema", name, "--type-name", "Person"]
    )
    runner.invoke(
        app, ["schema", "add-node-type", "--schema", name, "--type-name", "School"]
    )


def test_add_hyperedge_type_happy_path(_isolated_state_dir):
    _create_schema_with_node_types(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["schema", "add-hyperedge-type", "--schema", "s1", "--type-name", "ATTENDS",
         "--allowed-member", "Person", "--allowed-member", "School", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["name"] == "ATTENDS"
    assert data["allowed_member_types"] == ["Person", "School"]


def test_add_hyperedge_type_empty_allowed_member_permitted(_isolated_state_dir):
    """AME-1 — empty `allowed_member_types: []` permitted; mirrors EdgeType."""
    _create_schema_with_node_types(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["schema", "add-hyperedge-type", "--schema", "s1", "--type-name", "OPEN",
         "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["allowed_member_types"] == []


def test_add_hyperedge_type_invalid_cypher_type_exits_1(_isolated_state_dir):
    """Cypher rel-type regex enforced on --type-name (per ADR-0021)."""
    _create_schema_with_node_types(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["schema", "add-hyperedge-type", "--schema", "s1",
         "--type-name", "lower-case", "--allowed-member", "Person"],
    )
    assert res.exit_code == 1
    assert "CypherError" in (res.output + (res.stderr or ""))


def test_add_hyperedge_type_unknown_member_type_exits_1(_isolated_state_dir):
    """`--allowed-member` referencing unregistered NodeType → UnknownTypeError."""
    _create_schema_with_node_types(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["schema", "add-hyperedge-type", "--schema", "s1",
         "--type-name", "ATTENDS", "--allowed-member", "Nonexistent"],
    )
    assert res.exit_code == 1
    assert "UnknownTypeError" in (res.output + (res.stderr or ""))


def test_add_hyperedge_type_with_prop_types(_isolated_state_dir):
    """All 8 PropertyType variants accepted on --prop-type."""
    _create_schema_with_node_types(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["schema", "add-hyperedge-type", "--schema", "s1", "--type-name", "X",
         "--prop-type", "year=int",
         "--prop-type", "name=string",
         "--prop-type", "score=float",
         "--prop-type", "active=bool",
         "--prop-type", "tags=list[string]",
         "--prop-type", "counts=list[int]",
         "--prop-type", "weights=list[float]",
         "--prop-type", "flags=list[bool]",
         "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["property_types"]["year"] == "int"
    assert data["property_types"]["tags"] == "list[string]"
