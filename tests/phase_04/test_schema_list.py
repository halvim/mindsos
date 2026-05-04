"""Tests for ``mindsos schema list`` and ``mindsos schema reset``."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_list_empty_state_dir(_isolated_state_dir):
    res = runner.invoke(app, ["schema", "list", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["schemas"] == []


def test_list_multiple_sorted_by_name(_isolated_state_dir):
    for n in ["zeta", "alpha", "mu"]:
        runner.invoke(app, ["schema", "create", "--name", n])
    res = runner.invoke(app, ["schema", "list", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    names = [e["name"] for e in data["schemas"]]
    assert names == ["alpha", "mu", "zeta"]


def test_reset_by_name(_isolated_state_dir):
    runner.invoke(app, ["schema", "create", "--name", "s1"])
    res = runner.invoke(app, ["schema", "reset", "--name", "s1"])
    assert res.exit_code == 0
    assert not (_isolated_state_dir / "schema-s1.json").exists()


def test_reset_all(_isolated_state_dir):
    for n in ["a", "b", "c"]:
        runner.invoke(app, ["schema", "create", "--name", n])
    res = runner.invoke(app, ["schema", "reset", "--all", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert sorted(data["deleted"]) == ["a", "b", "c"]
    assert data["count"] == 3


def test_reset_neither_flag_exits_2(_isolated_state_dir):
    res = runner.invoke(app, ["schema", "reset"])
    assert res.exit_code == 2


def test_reset_both_flags_exits_2(_isolated_state_dir):
    res = runner.invoke(app, ["schema", "reset", "--name", "s1", "--all"])
    assert res.exit_code == 2


def test_reset_missing_name_exits_1(_isolated_state_dir):
    res = runner.invoke(app, ["schema", "reset", "--name", "ghost"])
    assert res.exit_code == 1
