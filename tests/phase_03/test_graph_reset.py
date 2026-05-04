"""Tests for ``mindsos graph reset``."""

from __future__ import annotations

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_reset_name_deletes_state_file(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    assert (_isolated_state_dir / "graph-g1.json").exists()
    res = runner.invoke(app, ["graph", "reset", "--name", "g1"])
    assert res.exit_code == 0, res.output
    assert not (_isolated_state_dir / "graph-g1.json").exists()


def test_reset_all_deletes_every_state_file(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(app, ["graph", "create", "--name", "g2"])
    runner.invoke(app, ["graph", "create", "--name", "g3"])
    res = runner.invoke(app, ["graph", "reset", "--all"])
    assert res.exit_code == 0, res.output
    assert list(_isolated_state_dir.glob("graph-*.json")) == []


def test_reset_no_flag_exits_2(_isolated_state_dir):
    res = runner.invoke(app, ["graph", "reset"])
    assert res.exit_code == 2


def test_reset_both_flags_exits_2(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    res = runner.invoke(app, ["graph", "reset", "--name", "g1", "--all"])
    assert res.exit_code == 2


def test_reset_missing_graph_exits_1(_isolated_state_dir):
    res = runner.invoke(app, ["graph", "reset", "--name", "missing"])
    assert res.exit_code == 1
