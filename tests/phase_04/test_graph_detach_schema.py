"""Tests for ``mindsos graph detach-schema`` (Phase 04 — Pick E + N1 + N6).

The detach command operates on the raw JSON dict so it works EVEN
WHEN the referenced schema state file has been deleted (the primary
recovery use case for dangling schema references).
"""

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


def test_detach_clears_schema_name(_isolated_state_dir):
    _strict_person_org(_isolated_state_dir)
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    res = runner.invoke(
        app, ["graph", "detach-schema", "--name", "g1", "--json"]
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["name"] == "g1"
    assert data["previous_schema"] == "s1"
    assert data["schema_name"] is None
    # Confirm in state file
    raw = json.loads(
        (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    )
    assert raw["schema_name"] is None
    # Subsequent inspect succeeds; schema field is None.
    res2 = runner.invoke(app, ["graph", "inspect", "--name", "g1", "--json"])
    assert res2.exit_code == 0
    assert json.loads(res2.output)["schema_name"] is None


def test_detach_with_dangling_reference_succeeds(_isolated_state_dir):
    """The primary recovery use case: schema deleted behind the graph's back."""
    _strict_person_org(_isolated_state_dir)
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    # Hand-delete the schema state file (simulating reset --force).
    (_isolated_state_dir / "schema-s1.json").unlink()
    # Confirm graph load fails via the standard path.
    res_inspect = runner.invoke(app, ["graph", "inspect", "--name", "g1"])
    assert res_inspect.exit_code == 1
    # detach-schema works regardless.
    res = runner.invoke(
        app, ["graph", "detach-schema", "--name", "g1", "--json"]
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["previous_schema"] == "s1"
    assert data["schema_name"] is None
    # Now inspect succeeds.
    res2 = runner.invoke(app, ["graph", "inspect", "--name", "g1"])
    assert res2.exit_code == 0


def test_detach_with_no_schema_attached_exits_1(_isolated_state_dir):
    """Phase 03 / 04 fail-loudly pattern on no-op."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    res = runner.invoke(app, ["graph", "detach-schema", "--name", "g1"])
    assert res.exit_code == 1
    assert "no schema attached" in res.output or "no schema attached" in (
        res.stderr or ""
    )


def test_detach_missing_graph_exits_1(_isolated_state_dir):
    res = runner.invoke(app, ["graph", "detach-schema", "--name", "ghost"])
    assert res.exit_code == 1
    assert "not found" in res.output or "not found" in (res.stderr or "")


def test_detach_invalid_name_exits_2(_isolated_state_dir):
    res = runner.invoke(app, ["graph", "detach-schema", "--name", "foo/bar"])
    assert res.exit_code == 2


def test_detach_writes_v2_state_file(_isolated_state_dir):
    """Detach upgrades the state file to v=2 if it was v=1."""
    # Hand-write a v=1 file with schema_name present (unusual but possible).
    legacy_state = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-000000000020",
        "name": "g1",
        "role": None,
        "schema_name": "s1",
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    (_isolated_state_dir / "graph-g1.json").write_text(
        json.dumps(legacy_state), encoding="utf-8"
    )
    res = runner.invoke(app, ["graph", "detach-schema", "--name", "g1"])
    assert res.exit_code == 0, res.output
    raw = json.loads(
        (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    )
    assert raw["_state_version"] == 2
    assert raw["schema_name"] is None


def test_detach_human_output_format(_isolated_state_dir):
    _strict_person_org(_isolated_state_dir)
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    res = runner.invoke(app, ["graph", "detach-schema", "--name", "g1"])
    assert res.exit_code == 0
    assert "detached schema='s1' from graph='g1'" in res.output
