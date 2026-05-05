"""Phase 04-v2 — UHT-1: `mindsos graph update-hyperedge-type` legacy-migration recovery."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _make_graph_with_hyperedge(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    for nid in ("a", "b"):
        runner.invoke(
            app,
            ["graph", "add-node", nid, "--name", "g1", "--type", "T",
             "--node-id", nid],
        )
    runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "UNSPECIFIED",
         "--member", "a", "--member", "b", "--hyperedge-id", "he-1"],
    )


def test_update_hyperedge_type_happy_path(_isolated_state_dir):
    """UNSPECIFIED → valid type updates cleanly; previous_type_name reported."""
    _make_graph_with_hyperedge(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "update-hyperedge-type", "--name", "g1",
         "--hyperedge-id", "he-1", "--type", "PAIR", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["previous_type_name"] == "UNSPECIFIED"
    assert data["new_type_name"] == "PAIR"


def test_update_hyperedge_type_invalid_cypher_exits_1(_isolated_state_dir):
    _make_graph_with_hyperedge(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "update-hyperedge-type", "--name", "g1",
         "--hyperedge-id", "he-1", "--type", "lower-case"],
    )
    assert res.exit_code == 1
    assert "CypherError" in (res.output + (res.stderr or ""))


def test_update_hyperedge_type_unknown_id_exits_1(_isolated_state_dir):
    _make_graph_with_hyperedge(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "update-hyperedge-type", "--name", "g1",
         "--hyperedge-id", "ghost", "--type", "PAIR"],
    )
    assert res.exit_code == 1
    assert "IdentityError" in (res.output + (res.stderr or ""))


def test_update_hyperedge_type_idempotent_noop(_isolated_state_dir):
    """No-op idempotent (UNSPECIFIED→UNSPECIFIED) exits 0; file rewritten."""
    _make_graph_with_hyperedge(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "update-hyperedge-type", "--name", "g1",
         "--hyperedge-id", "he-1", "--type", "UNSPECIFIED", "--json"],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["previous_type_name"] == "UNSPECIFIED"
    assert data["new_type_name"] == "UNSPECIFIED"


def test_update_hyperedge_type_under_strict_schema_member_check(_isolated_state_dir):
    """Schema attached: new type's allowed_member_types validated."""
    runner.invoke(app, ["schema", "create", "--name", "s1", "--strict"])
    runner.invoke(
        app,
        ["schema", "add-node-type", "--schema", "s1", "--type-name", "Person"],
    )
    runner.invoke(
        app,
        ["schema", "add-hyperedge-type", "--schema", "s1",
         "--type-name", "ATTENDS", "--allowed-member", "Person"],
    )
    runner.invoke(app, ["graph", "create", "--name", "g1", "--schema", "s1"])
    runner.invoke(
        app,
        ["graph", "add-node", "Alice", "--name", "g1", "--type", "Person",
         "--node-id", "a"],
    )
    runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "ATTENDS",
         "--member", "a", "--hyperedge-id", "he-1"],
    )
    # Update to an unregistered HyperEdgeType → UnknownTypeError.
    res = runner.invoke(
        app,
        ["graph", "update-hyperedge-type", "--name", "g1",
         "--hyperedge-id", "he-1", "--type", "UNREGISTERED"],
    )
    assert res.exit_code == 1
    assert "UnknownTypeError" in (res.output + (res.stderr or ""))
