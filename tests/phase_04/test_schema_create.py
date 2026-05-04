"""Tests for ``mindsos schema create``."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_create_writes_state_file(_isolated_state_dir):
    res = runner.invoke(app, ["schema", "create", "--name", "s1"])
    assert res.exit_code == 0, res.output
    assert (_isolated_state_dir / "schema-s1.json").exists()


def test_create_default_is_non_strict(_isolated_state_dir):
    res = runner.invoke(app, ["schema", "create", "--name", "s1", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["name"] == "s1"
    assert data["strict"] is False


def test_create_with_strict_flag(_isolated_state_dir):
    res = runner.invoke(
        app, ["schema", "create", "--name", "s1", "--strict", "--json"]
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["strict"] is True


def test_create_duplicate_name_exits_1(_isolated_state_dir):
    res1 = runner.invoke(app, ["schema", "create", "--name", "s1"])
    assert res1.exit_code == 0
    res2 = runner.invoke(app, ["schema", "create", "--name", "s1"])
    assert res2.exit_code == 1
    assert "already exists" in res2.output or "already exists" in (res2.stderr or "")


def test_create_invalid_name_exits_2(_isolated_state_dir):
    res = runner.invoke(app, ["schema", "create", "--name", "foo/bar"])
    assert res.exit_code == 2
