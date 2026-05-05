"""Phase 04-v2 — `set-prop --hyperedge-id` mutex extension."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _setup(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    for nid in ("a", "b"):
        runner.invoke(
            app,
            ["graph", "add-node", nid, "--name", "g1", "--type", "T",
             "--node-id", nid],
        )
    runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "PAIR",
         "--member", "a", "--member", "b", "--hyperedge-id", "he-1",
         "--prop", "year=2024"],
    )


def test_set_prop_hyperedge_id_mutex_happy(_isolated_state_dir):
    _setup(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "set-prop", "--name", "g1", "--hyperedge-id", "he-1",
         "--prop", "since=2025", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["kind"] == "hyperedge"
    assert data["properties"]["year"] == 2024
    assert data["properties"]["since"] == 2025


def test_set_prop_3way_mutex_rejects_two(_isolated_state_dir):
    """Phase 04-v2 — 3-way mutex; supplying two flags exits 2."""
    _setup(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "set-prop", "--name", "g1", "--node-id", "a",
         "--hyperedge-id", "he-1", "--prop", "k=v"],
    )
    assert res.exit_code == 2


def test_set_prop_hyperedge_replace_preserves_refs(_isolated_state_dir):
    """`--replace` on hyperedge preserves `ref:*` keys per Phase 04 Pick D + N5."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(
        app,
        ["graph", "add-node", "a", "--name", "g1", "--type", "T", "--node-id", "a"],
    )
    runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "PAIR",
         "--member", "a", "--hyperedge-id", "he-1",
         "--prop", "year=2024", "--prop", "ref:source=alpha-uuid"],
    )
    res = runner.invoke(
        app,
        ["graph", "set-prop", "--name", "g1", "--hyperedge-id", "he-1",
         "--replace", "--prop", "score=99", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    # ref:* preserved; year DROPPED on --replace.
    assert "ref:source" in data["properties"]
    assert data["properties"]["ref:source"] == "alpha-uuid"
    assert data["properties"]["score"] == 99
    assert "year" not in data["properties"]
