"""Cross-invocation state persistence — round-trip tests.

These tests use ``CliRunner`` (in-process) but each invoke is conceptually
a fresh CLI run; the state survives across them because the autouse
fixture sets ``MINDSOS_STATE_DIR`` once per test.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_round_trip_full_graph(_isolated_state_dir):
    """Build a graph (≥3 nodes, ≥2 edges, ≥1 hyperedge) across multiple invocations."""
    runner.invoke(app, ["graph", "create", "--name", "g1", "--role", "ontology"])
    for nid in ("a", "b", "c"):
        runner.invoke(
            app,
            ["graph", "add-node", nid, "--name", "g1", "--type", "T",
             "--node-id", nid],
        )
    runner.invoke(
        app,
        ["graph", "add-edge", "--name", "g1", "--source", "a",
         "--target", "b", "--type", "REL_X"],
    )
    runner.invoke(
        app,
        ["graph", "add-edge", "--name", "g1", "--source", "b",
         "--target", "c", "--type", "REL_Y"],
    )
    runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "TRIO",
         "--member", "a", "--member", "b", "--member", "c"],
    )

    res = runner.invoke(app, ["graph", "inspect", "--name", "g1", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["counts"] == {"nodes": 3, "edges": 2, "hyperedges": 1}


def test_state_file_has_state_version(_isolated_state_dir):
    """State files always carry ``_state_version``.

    Phase 03 wrote v=1; Phase 04 BUMPED to v=2 (added optional
    ``schema_name`` field). This test now asserts the field exists and
    matches the writer's current ``GRAPH_STATE_VERSION`` rather than
    pinning a specific number — the bump is intentional per
    PHASE_MAP §1 "Breaking changes between phases allowed".
    """
    from mindsos_cli import state as state_mod
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    raw = (_isolated_state_dir / "graph-g1.json").read_text()
    state = json.loads(raw)
    assert state["_state_version"] == state_mod.GRAPH_STATE_VERSION


def test_state_file_lists_sorted_by_id(_isolated_state_dir):
    """nodes / edges / hyperedges arrays are sorted by id on save."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    # Add nodes out of id order
    for nid in ("zebra", "alpha", "midway"):
        runner.invoke(
            app,
            ["graph", "add-node", nid, "--name", "g1", "--type", "T",
             "--node-id", nid],
        )
    state = json.loads(
        (_isolated_state_dir / "graph-g1.json").read_text()
    )
    node_ids = [n["node_id"] for n in state["nodes"]]
    assert node_ids == sorted(node_ids)
    assert node_ids == ["alpha", "midway", "zebra"]


def test_state_file_hyperedge_member_ids_sorted(_isolated_state_dir):
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    for nid in ("c", "a", "b"):
        runner.invoke(
            app,
            ["graph", "add-node", nid, "--name", "g1", "--type", "T",
             "--node-id", nid],
        )
    runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "TRIO",
         "--member", "c", "--member", "a", "--member", "b"],
    )
    state = json.loads(
        (_isolated_state_dir / "graph-g1.json").read_text()
    )
    assert state["hyperedges"][0]["member_ids"] == ["a", "b", "c"]
