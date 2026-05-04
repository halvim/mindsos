"""Tests for ``mindsos schema reset`` orphan check (Phase 04 — Pick F + NEW3).

The reset command refuses to delete a schema if any graph references it
via the graph state file's ``schema_name`` field. ``--force`` overrides;
the resulting graphs need ``mindsos graph detach-schema`` to recover.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _seed_schema(name: str = "s1") -> None:
    runner.invoke(app, ["schema", "create", "--name", name])
    runner.invoke(
        app, ["schema", "add-node-type", "--schema", name, "--type-name", "Person"]
    )


def test_reset_name_with_orphan_refuses(_isolated_state_dir):
    _seed_schema("s1")
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    res = runner.invoke(app, ["schema", "reset", "--name", "s1"])
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "Refusing to reset" in output
    assert "g1" in output
    assert "s1" in output
    # Schema NOT deleted.
    assert (_isolated_state_dir / "schema-s1.json").exists()


def test_reset_name_with_orphan_force_proceeds(_isolated_state_dir):
    _seed_schema("s1")
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    res = runner.invoke(
        app, ["schema", "reset", "--name", "s1", "--force", "--json"]
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["force"] is True
    assert "s1" in data["deleted"]
    # Schema deleted.
    assert not (_isolated_state_dir / "schema-s1.json").exists()
    # Graph still has dangling reference.
    raw = json.loads(
        (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    )
    assert raw["schema_name"] == "s1"


def test_reset_name_no_orphan_proceeds(_isolated_state_dir):
    _seed_schema("s1")
    runner.invoke(app, ["graph", "create", "--name", "g1"])  # no schema attached
    res = runner.invoke(app, ["schema", "reset", "--name", "s1"])
    assert res.exit_code == 0, res.output
    assert not (_isolated_state_dir / "schema-s1.json").exists()


def test_reset_all_with_orphan_refuses(_isolated_state_dir):
    """--all mode also runs the orphan check (NEW3)."""
    _seed_schema("s1")
    _seed_schema("s2")
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s2"])
    res = runner.invoke(app, ["schema", "reset", "--all"])
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "g1" in output
    assert "s2" in output
    # Neither schema deleted.
    assert (_isolated_state_dir / "schema-s1.json").exists()
    assert (_isolated_state_dir / "schema-s2.json").exists()


def test_reset_all_with_orphan_force_proceeds(_isolated_state_dir):
    _seed_schema("s1")
    _seed_schema("s2")
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s2"])
    res = runner.invoke(
        app, ["schema", "reset", "--all", "--force", "--json"]
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert sorted(data["deleted"]) == ["s1", "s2"]
    assert data["force"] is True


def test_reset_all_no_orphan_proceeds(_isolated_state_dir):
    _seed_schema("s1")
    _seed_schema("s2")
    runner.invoke(app, ["graph", "create", "--name", "g1"])  # no schema
    res = runner.invoke(app, ["schema", "reset", "--all"])
    assert res.exit_code == 0
    assert not (_isolated_state_dir / "schema-s1.json").exists()
    assert not (_isolated_state_dir / "schema-s2.json").exists()


def test_reset_orphan_check_skips_unreadable_graph(_isolated_state_dir):
    """An unreadable graph state file is skipped with a warning, not crashed on."""
    _seed_schema("s1")
    # Hand-write a corrupt graph state file.
    (_isolated_state_dir / "graph-corrupt.json").write_text(
        "{not valid json", encoding="utf-8"
    )
    # Reset still proceeds (the corrupt graph is skipped — it can't reference s1).
    res = runner.invoke(app, ["schema", "reset", "--name", "s1"])
    assert res.exit_code == 0


def test_reset_force_emits_warning_about_dangling(_isolated_state_dir):
    """--force emits a stderr warning naming the recovery command."""
    _seed_schema("s1")
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    res = runner.invoke(app, ["schema", "reset", "--name", "s1", "--force"])
    assert res.exit_code == 0
    output = res.output + (res.stderr or "")
    assert "detach-schema" in output
