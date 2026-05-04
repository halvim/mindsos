"""Tests for ``mindsos graph attach-schema`` (eager validation, Phase 04)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _strict_person_org(_isolated_state_dir, schema_name: str = "s1") -> None:
    runner.invoke(app, ["schema", "create", "--name", schema_name, "--strict"])
    runner.invoke(
        app,
        [
            "schema",
            "add-node-type",
            "--schema",
            schema_name,
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
            schema_name,
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
            schema_name,
            "--type-name",
            "WORKS_AT",
            "--allowed-source",
            "Person",
            "--allowed-target",
            "Org",
        ],
    )


def _seed_conformant_graph(_isolated_state_dir, name: str = "g1") -> None:
    """Build a graph (no schema) whose data WILL conform to the strict schema."""
    runner.invoke(app, ["graph", "create", "--name", name])
    runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "Alice",
            "--name",
            name,
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
            "Acme",
            "--name",
            name,
            "--type",
            "Org",
            "--node-id",
            "n-b",
        ],
    )
    runner.invoke(
        app,
        [
            "graph",
            "add-edge",
            "--name",
            name,
            "--source",
            "n-a",
            "--target",
            "n-b",
            "--type",
            "WORKS_AT",
        ],
    )


def test_attach_schema_succeeds_on_conformant_data(_isolated_state_dir):
    _strict_person_org(_isolated_state_dir)
    _seed_conformant_graph(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "attach-schema", "--name", "g1", "--schema", "s1", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["schema_name"] == "s1"
    assert data["validated"]["nodes"] == 2
    assert data["validated"]["edges"] == 1
    # Round-trip: schema_name is now in the graph state file.
    raw = (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    assert json.loads(raw)["schema_name"] == "s1"


def test_attach_schema_rejects_unknown_node_type(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "x",
            "--name",
            "g1",
            "--type",
            "Alien",  # not in the schema we're about to attach
        ],
    )
    _strict_person_org(_isolated_state_dir)
    res = runner.invoke(
        app, ["graph", "attach-schema", "--name", "g1", "--schema", "s1"]
    )
    assert res.exit_code == 1
    assert "UnknownTypeError" in res.output or "UnknownTypeError" in (res.stderr or "")
    assert "NOT attached" in res.output or "NOT attached" in (res.stderr or "")


def test_attach_schema_rejects_property_shape_violation(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "g1"])
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
            "--prop",
            "age=thirty",  # string — violates strict int schema
        ],
    )
    _strict_person_org(_isolated_state_dir)
    res = runner.invoke(
        app, ["graph", "attach-schema", "--name", "g1", "--schema", "s1"]
    )
    assert res.exit_code == 1
    assert "PropertyShapeError" in res.output or "PropertyShapeError" in (
        res.stderr or ""
    )


def test_attach_schema_rejection_leaves_graph_state_unchanged(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "g1"])
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
            "--prop",
            "age=thirty",
        ],
    )
    _strict_person_org(_isolated_state_dir)
    before = (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    runner.invoke(
        app, ["graph", "attach-schema", "--name", "g1", "--schema", "s1"]
    )
    after = (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    assert before == after


def test_attach_missing_schema_exits_1(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    res = runner.invoke(
        app, ["graph", "attach-schema", "--name", "g1", "--schema", "ghost"]
    )
    assert res.exit_code == 1
    assert "not found" in res.output or "not found" in (res.stderr or "")


def test_attach_to_missing_graph_exits_1(_isolated_state_dir):
    _strict_person_org(_isolated_state_dir)
    res = runner.invoke(
        app, ["graph", "attach-schema", "--name", "ghost", "--schema", "s1"]
    )
    assert res.exit_code == 1


def test_attach_schema_rejects_disallowed_edge_endpoints(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "g1"])
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
    runner.invoke(
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
    _strict_person_org(_isolated_state_dir)
    res = runner.invoke(
        app, ["graph", "attach-schema", "--name", "g1", "--schema", "s1"]
    )
    assert res.exit_code == 1
    # Edge endpoint type mismatch surfaces as UnknownTypeError.
    assert "UnknownTypeError" in res.output or "UnknownTypeError" in (res.stderr or "")


# ── Phase 04 — Pick B: error includes offending element id ────────────────


def test_attach_error_includes_offending_node_id(_isolated_state_dir):
    """Eager-attach error message names the failing node id (Pick B)."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
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
            "the-bad-node",
            "--prop",
            "age=thirty",  # string violates strict int schema
        ],
    )
    _strict_person_org(_isolated_state_dir)
    res = runner.invoke(
        app, ["graph", "attach-schema", "--name", "g1", "--schema", "s1"]
    )
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "the-bad-node" in output
    assert "node" in output  # the kind label
    assert "PropertyShapeError" in output


def test_attach_error_includes_offending_edge_id(_isolated_state_dir):
    """Edge errors carry the edge id too."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
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
    runner.invoke(
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
            "--edge-id",
            "the-bad-edge",
        ],
    )
    _strict_person_org(_isolated_state_dir)
    res = runner.invoke(
        app, ["graph", "attach-schema", "--name", "g1", "--schema", "s1"]
    )
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "the-bad-edge" in output
    assert "edge" in output


# ── Phase 04 — Pick N4: re-attach replaces existing schema ────────────────


def test_attach_schema_replaces_existing_schema(_isolated_state_dir):
    """Re-attach is allowed; new schema replaces the old."""
    # First schema: non-strict, allows Person + Org.
    runner.invoke(app, ["schema", "create", "--name", "s1"])
    runner.invoke(
        app, ["schema", "add-node-type", "--schema", "s1", "--type-name", "Person"]
    )
    runner.invoke(
        app, ["schema", "add-node-type", "--schema", "s1", "--type-name", "Org"]
    )
    # Second schema: strict, also allows Person + Org but with strict typing.
    runner.invoke(app, ["schema", "create", "--name", "s2", "--strict"])
    runner.invoke(
        app,
        [
            "schema",
            "add-node-type",
            "--schema",
            "s2",
            "--type-name",
            "Person",
            "--prop-type",
            "age=int",
        ],
    )
    runner.invoke(
        app, ["schema", "add-node-type", "--schema", "s2", "--type-name", "Org"]
    )

    # Build a graph attached to s1 with conformant data.
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
            "--prop",
            "age=30",
        ],
    )
    # Re-attach with s2 — succeeds because age=30 (int) conforms.
    res = runner.invoke(
        app,
        ["graph", "attach-schema", "--name", "g1", "--schema", "s2", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["schema_name"] == "s2"
    assert data["previous_schema"] == "s1"
    assert data["strict"] is True


def test_reattach_with_incompatible_schema_rejects(_isolated_state_dir):
    """Re-attach with a schema that rejects existing data exits 1."""
    # s1 non-strict.
    runner.invoke(app, ["schema", "create", "--name", "s1"])
    runner.invoke(
        app, ["schema", "add-node-type", "--schema", "s1", "--type-name", "Person"]
    )
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
            "--prop",
            "age=thirty",
        ],
    )
    # s2 strict requires age=int.
    runner.invoke(app, ["schema", "create", "--name", "s2", "--strict"])
    runner.invoke(
        app,
        [
            "schema",
            "add-node-type",
            "--schema",
            "s2",
            "--type-name",
            "Person",
            "--prop-type",
            "age=int",
        ],
    )
    res = runner.invoke(
        app, ["graph", "attach-schema", "--name", "g1", "--schema", "s2"]
    )
    assert res.exit_code == 1
    # Confirm s1 is still attached (re-attach was rejected).
    res2 = runner.invoke(app, ["graph", "inspect", "--name", "g1", "--json"])
    assert res2.exit_code == 0
    assert json.loads(res2.output)["schema_name"] == "s1"


def test_attach_schema_json_includes_previous_schema_on_first_attach(
    _isolated_state_dir,
):
    """First attach has previous_schema = None."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    _strict_person_org(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "attach-schema", "--name", "g1", "--schema", "s1", "--json"],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["previous_schema"] is None


# ── Phase 04 — Pick G: empty-strict-schema warning ────────────────────────


def test_attach_empty_strict_schema_warns(_isolated_state_dir):
    """Attaching a strict schema with zero NodeTypes emits a stderr warning."""
    runner.invoke(app, ["schema", "create", "--name", "empty-strict", "--strict"])
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    res = runner.invoke(
        app, ["graph", "attach-schema", "--name", "g1", "--schema", "empty-strict"]
    )
    assert res.exit_code == 0
    output = res.output + (res.stderr or "")
    assert "warning" in output.lower()
    assert "zero NodeTypes" in output or "zero nodetypes" in output.lower()


def test_attach_empty_non_strict_schema_no_warning(_isolated_state_dir):
    """Empty non-strict schema does NOT trigger the warning."""
    runner.invoke(app, ["schema", "create", "--name", "empty-loose"])
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    res = runner.invoke(
        app, ["graph", "attach-schema", "--name", "g1", "--schema", "empty-loose"]
    )
    assert res.exit_code == 0
    output = (res.output + (res.stderr or "")).lower()
    assert "zero nodetypes" not in output
