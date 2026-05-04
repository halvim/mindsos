"""Tests for ``mindsos schema add-edge-type``."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _seed_schema(name: str = "s1", *, with_node_types: bool = True) -> None:
    res = runner.invoke(app, ["schema", "create", "--name", name])
    assert res.exit_code == 0
    if with_node_types:
        for nt in ("Person", "Org"):
            res = runner.invoke(
                app, ["schema", "add-node-type", "--schema", name, "--type-name", nt]
            )
            assert res.exit_code == 0


def test_add_edge_type_happy_path(_isolated_state_dir):
    _seed_schema()
    res = runner.invoke(
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
            "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["name"] == "WORKS_AT"
    assert data["allowed_sources"] == ["Person"]
    assert data["allowed_targets"] == ["Org"]


def test_add_edge_type_lowercase_rel_type_exits_1(_isolated_state_dir):
    _seed_schema()
    res = runner.invoke(
        app,
        [
            "schema",
            "add-edge-type",
            "--schema",
            "s1",
            "--type-name",
            "works_at",  # lowercase rejected by Cypher rel-type regex (ADR-0021)
        ],
    )
    assert res.exit_code == 1
    assert "CypherError" in res.output or "CypherError" in (res.stderr or "")


def test_add_edge_type_mixed_case_rel_type_exits_1(_isolated_state_dir):
    _seed_schema()
    res = runner.invoke(
        app,
        [
            "schema",
            "add-edge-type",
            "--schema",
            "s1",
            "--type-name",
            "Works_At",
        ],
    )
    assert res.exit_code == 1
    assert "CypherError" in res.output or "CypherError" in (res.stderr or "")


def test_add_edge_type_unknown_allowed_source_exits_1(_isolated_state_dir):
    _seed_schema(with_node_types=False)  # no NodeTypes registered
    res = runner.invoke(
        app,
        [
            "schema",
            "add-edge-type",
            "--schema",
            "s1",
            "--type-name",
            "WORKS_AT",
            "--allowed-source",
            "Ghost",
        ],
    )
    assert res.exit_code == 1
    assert "UnknownTypeError" in res.output or "UnknownTypeError" in (res.stderr or "")


def test_add_edge_type_duplicate_exits_1(_isolated_state_dir):
    _seed_schema()
    runner.invoke(
        app, ["schema", "add-edge-type", "--schema", "s1", "--type-name", "WORKS_AT"]
    )
    res = runner.invoke(
        app, ["schema", "add-edge-type", "--schema", "s1", "--type-name", "WORKS_AT"]
    )
    assert res.exit_code == 1


def test_add_edge_type_with_prop_types(_isolated_state_dir):
    _seed_schema()
    res = runner.invoke(
        app,
        [
            "schema",
            "add-edge-type",
            "--schema",
            "s1",
            "--type-name",
            "WORKS_AT",
            "--prop-type",
            "since=int",
            "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["property_types"] == {"since": "int"}


def test_add_edge_type_no_constraints_means_any(_isolated_state_dir):
    """Empty allowed sets = any source / any target (parent project semantics)."""
    _seed_schema()
    res = runner.invoke(
        app,
        [
            "schema",
            "add-edge-type",
            "--schema",
            "s1",
            "--type-name",
            "REL",
            "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["allowed_sources"] == []
    assert data["allowed_targets"] == []
