"""Tests for ``mindsos graph create --schema <NAME>`` and round-trip."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _make_strict_person_org_schema(_isolated_state_dir, name: str = "s1") -> None:
    runner.invoke(app, ["schema", "create", "--name", name, "--strict"])
    runner.invoke(
        app,
        [
            "schema",
            "add-node-type",
            "--schema",
            name,
            "--type-name",
            "Person",
            "--prop-type",
            "age=int",
        ],
    )
    runner.invoke(
        app,
        ["schema", "add-node-type", "--schema", name, "--type-name", "Org"],
    )
    runner.invoke(
        app,
        [
            "schema",
            "add-edge-type",
            "--schema",
            name,
            "--type-name",
            "WORKS_AT",
            "--allowed-source",
            "Person",
            "--allowed-target",
            "Org",
        ],
    )


def test_graph_create_with_schema_attaches(_isolated_state_dir):
    _make_strict_person_org_schema(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "create", "--name", "g1", "--schema", "s1", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["schema_name"] == "s1"


def test_graph_create_with_missing_schema_exits_1(_isolated_state_dir):
    res = runner.invoke(
        app,
        ["graph", "create", "--name", "g1", "--schema", "ghost"],
    )
    assert res.exit_code == 1
    assert "not found" in res.output or "not found" in (res.stderr or "")


def test_graph_create_without_schema_keeps_schema_name_null(_isolated_state_dir):
    res = runner.invoke(app, ["graph", "create", "--name", "g1", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["schema_name"] is None


def test_graph_inspect_reports_attached_schema(_isolated_state_dir):
    _make_strict_person_org_schema(_isolated_state_dir)
    runner.invoke(
        app, ["graph", "create", "--name", "g1", "--schema", "s1"]
    )
    res = runner.invoke(app, ["graph", "inspect", "--name", "g1", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["schema_name"] == "s1"
    assert data["schema_strict"] is True


def test_add_node_under_schema_validates_type(_isolated_state_dir):
    _make_strict_person_org_schema(_isolated_state_dir)
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    # Unknown node type → exit 1
    res = runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "Alien",
            "--name",
            "g1",
            "--type",
            "Alien",
        ],
    )
    assert res.exit_code == 1
    assert "UnknownTypeError" in res.output or "UnknownTypeError" in (res.stderr or "")


def test_add_node_strict_property_type_mismatch_exits_1(_isolated_state_dir):
    _make_strict_person_org_schema(_isolated_state_dir)
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    # age must be int (per the strict schema); pass a string
    res = runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "Alice",
            "--name",
            "g1",
            "--type",
            "Person",
            "--prop",
            "age=thirty",
        ],
    )
    assert res.exit_code == 1
    assert "PropertyShapeError" in res.output or "PropertyShapeError" in (res.stderr or "")


def test_add_edge_strict_source_type_mismatch_exits_1(_isolated_state_dir):
    _make_strict_person_org_schema(_isolated_state_dir)
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "Alice",
            "--name",
            "g1",
            "--type",
            "Person",
            "--node-id",
            "n-a",
            "--prop",
            "age=30",
        ],
    )
    runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "Bob",
            "--name",
            "g1",
            "--type",
            "Person",
            "--node-id",
            "n-b",
            "--prop",
            "age=25",
        ],
    )
    # WORKS_AT requires source=Person, target=Org. Person → Person violates target.
    res = runner.invoke(
        app,
        [
            "graph",
            "add-edge",
            "--name",
            "g1",
            "--source",
            "n-a",
            "--target",
            "n-b",
            "--type",
            "WORKS_AT",
        ],
    )
    assert res.exit_code == 1
    assert "UnknownTypeError" in res.output or "UnknownTypeError" in (res.stderr or "")


def test_graph_state_file_round_trips_schema_name(_isolated_state_dir):
    _make_strict_person_org_schema(_isolated_state_dir)
    runner.invoke(
        app, ["graph", "create", "--name", "g1", "--schema", "s1"]
    )
    raw = (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    state = json.loads(raw)
    assert state["schema_name"] == "s1"
    # Subsequent inspect re-loads the schema from disk and the field survives.
    res = runner.invoke(app, ["graph", "inspect", "--name", "g1", "--json"])
    assert res.exit_code == 0
    assert json.loads(res.output)["schema_name"] == "s1"


def test_graph_with_dangling_schema_ref_fails_to_load(_isolated_state_dir):
    _make_strict_person_org_schema(_isolated_state_dir)
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    # Now delete the schema state file behind the graph's back.
    (_isolated_state_dir / "schema-s1.json").unlink()
    res = runner.invoke(app, ["graph", "inspect", "--name", "g1"])
    assert res.exit_code == 1
    assert "not found" in res.output or "not found" in (res.stderr or "")
