"""Phase 04-v2 — eager attach validation extends to hyperedges."""

from __future__ import annotations

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _create_strict_schema_no_hyperedge_type(_isolated_state_dir):
    runner.invoke(app, ["schema", "create", "--name", "s1", "--strict"])
    runner.invoke(
        app, ["schema", "add-node-type", "--schema", "s1", "--type-name", "Person"]
    )
    # NO hyperedge_types — strict schema with zero HyperEdgeTypes.


def test_attach_strict_schema_with_hyperedge_violation_refuses(_isolated_state_dir):
    """Eager validation: a hyperedge whose type isn't registered → exit 1."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    for nid in ("a", "b"):
        runner.invoke(
            app,
            ["graph", "add-node", nid, "--name", "g1", "--type", "Person",
             "--node-id", nid],
        )
    runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "TRIO",
         "--member", "a", "--member", "b", "--hyperedge-id", "he-1"],
    )
    _create_strict_schema_no_hyperedge_type(_isolated_state_dir)
    res = runner.invoke(
        app, ["graph", "attach-schema", "--name", "g1", "--schema", "s1"]
    )
    assert res.exit_code == 1
    # First violation surfaces hyperedge_id.
    assert "he-1" in (res.output + (res.stderr or ""))
    assert "hyperedge" in (res.output + (res.stderr or "")).lower()


def test_attach_validation_order_node_edge_hyperedge(_isolated_state_dir):
    """Eager attach validation order: every Node, then every Edge, then every HyperEdge.

    Phase 04-v2 row appendix item 14 lock.
    """
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(
        app,
        ["graph", "add-node", "Alice", "--name", "g1", "--type", "BogusNodeType",
         "--node-id", "a"],
    )
    # Strict schema doesn't register BogusNodeType.
    _create_strict_schema_no_hyperedge_type(_isolated_state_dir)
    res = runner.invoke(
        app, ["graph", "attach-schema", "--name", "g1", "--schema", "s1"]
    )
    assert res.exit_code == 1
    # NODE violation surfaces first (validation order: nodes before hyperedges).
    assert "node" in (res.output + (res.stderr or "")).lower()
    assert "a" in (res.output + (res.stderr or ""))


def test_attach_failure_leaves_file_unchanged(_isolated_state_dir):
    """Failed attach does NOT upgrade state-file (validation runs in-memory)."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(
        app,
        ["graph", "add-node", "Alice", "--name", "g1", "--type", "BogusType",
         "--node-id", "a"],
    )
    _create_strict_schema_no_hyperedge_type(_isolated_state_dir)
    # Capture file timestamp / content before
    path = _isolated_state_dir / "graph-g1.json"
    before = path.read_text()
    res = runner.invoke(
        app, ["graph", "attach-schema", "--name", "g1", "--schema", "s1"]
    )
    assert res.exit_code == 1
    after = path.read_text()
    assert before == after  # state-file unchanged.
