"""Tests for ``mindsos graph add-hyperedge``."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _setup_three_nodes(_isolated_state_dir, name="g1"):
    runner.invoke(app, ["graph", "create", "--name", name])
    for nid in ("a", "b", "c"):
        runner.invoke(
            app,
            ["graph", "add-node", nid, "--name", name, "--type", "T",
             "--node-id", nid],
        )


def test_add_hyperedge_happy_path(_isolated_state_dir):
    _setup_three_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1",
         "--member", "a", "--member", "b", "--member", "c",
         "--label", "trio", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["member_ids"] == ["a", "b", "c"]
    assert data["label"] == "trio"


def test_add_hyperedge_empty_members_exits_2(_isolated_state_dir):
    """Typer rejects no `--member` (Option default is empty list); empty list reaches Graph.add_hyperedge → SchemaError."""
    _setup_three_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1"],
    )
    # No --member flag → empty list → SchemaError on add_hyperedge → exit 1
    assert res.exit_code == 1
    assert "SchemaError" in (res.output + (res.stderr or ""))


def test_add_hyperedge_canonicalises_member_order(_isolated_state_dir):
    """member_ids in JSON output is sorted regardless of input order."""
    _setup_three_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1",
         "--member", "c", "--member", "a", "--member", "b",
         "--json"],
    )
    data = json.loads(res.output)
    assert data["member_ids"] == ["a", "b", "c"]  # sorted, not c-a-b


def test_add_hyperedge_unknown_member_exits_1(_isolated_state_dir):
    _setup_three_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1",
         "--member", "a", "--member", "missing"],
    )
    assert res.exit_code == 1
    assert "IdentityError" in (res.output + (res.stderr or ""))


def test_add_hyperedge_explicit_id(_isolated_state_dir):
    _setup_three_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1",
         "--member", "a", "--member", "b",
         "--hyperedge-id", "he-1", "--json"],
    )
    data = json.loads(res.output)
    assert data["edge_id"] == "he-1"
