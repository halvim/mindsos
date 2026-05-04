"""Tests for ``mindsos graph set-prop`` (Phase 04).

Phase 04 — Pick I: ``--node`` / ``--edge`` were renamed to
``--node-id`` / ``--edge-id`` for parity with ``add-node --node-id``.
Phase 04 — Pick D + N5: ``--replace`` preserves ``ref:*`` keys;
user-supplied ``ref:*`` values overwrite existing on collision.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _seed_simple_graph(_isolated_state_dir, *, with_schema: bool = False) -> None:
    if with_schema:
        runner.invoke(app, ["schema", "create", "--name", "s1", "--strict"])
        runner.invoke(
            app,
            [
                "schema",
                "add-node-type",
                "--schema",
                "s1",
                "--type-name",
                "Person",
                "--prop-type",
                "age=int",
            ],
        )
        runner.invoke(
            app,
            ["schema", "add-node-type", "--schema", "s1", "--type-name", "Org"],
        )
        runner.invoke(
            app,
            [
                "schema",
                "add-edge-type",
                "--schema",
                "s1",
                "--type-name",
                "WORKS_AT",
                "--allowed-source",
                "Person",
                "--allowed-target",
                "Org",
                "--prop-type",
                "since=int",
            ],
        )
        runner.invoke(
            app, ["graph", "create", "--name", "g1", "--schema", "s1"]
        )
    else:
        runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "Alice",
            "--name",
            "g1",
            "--type",
            "Person",
            "--node-id",
            "n-a",
            "--prop",
            "age=30",
        ],
    )
    runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "Acme",
            "--name",
            "g1",
            "--type",
            "Org",
            "--node-id",
            "n-b",
        ],
    )
    runner.invoke(
        app,
        [
            "graph",
            "add-edge",
            "--name",
            "g1",
            "--source",
            "n-a",
            "--target",
            "n-b",
            "--type",
            "WORKS_AT",
            "--edge-id",
            "e-1",
            "--prop",
            "since=2020",
        ],
    )


def test_set_prop_node_merge(_isolated_state_dir):
    _seed_simple_graph(_isolated_state_dir)
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--node-id",
            "n-a",
            "--prop",
            "city=NYC",
            "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["properties"] == {"age": 30, "city": "NYC"}


def test_set_prop_node_replace(_isolated_state_dir):
    _seed_simple_graph(_isolated_state_dir)
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--node-id",
            "n-a",
            "--prop",
            "city=NYC",
            "--replace",
            "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["properties"] == {"city": "NYC"}


def test_set_prop_edge_merge(_isolated_state_dir):
    _seed_simple_graph(_isolated_state_dir)
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--edge-id",
            "e-1",
            "--prop",
            "weight=0.7",
            "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["properties"] == {"since": 2020, "weight": 0.7}


def test_set_prop_edge_replace(_isolated_state_dir):
    _seed_simple_graph(_isolated_state_dir)
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--edge-id",
            "e-1",
            "--prop",
            "weight=0.7",
            "--replace",
            "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["properties"] == {"weight": 0.7}


def test_set_prop_both_node_and_edge_exits_2(_isolated_state_dir):
    _seed_simple_graph(_isolated_state_dir)
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--node-id",
            "n-a",
            "--edge-id",
            "e-1",
            "--prop",
            "x=1",
        ],
    )
    assert res.exit_code == 2


def test_set_prop_neither_node_nor_edge_exits_2(_isolated_state_dir):
    _seed_simple_graph(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "set-prop", "--name", "g1", "--prop", "x=1"],
    )
    assert res.exit_code == 2


def test_set_prop_no_props_exits_2(_isolated_state_dir):
    _seed_simple_graph(_isolated_state_dir)
    res = runner.invoke(
        app, ["graph", "set-prop", "--name", "g1", "--node-id", "n-a"]
    )
    assert res.exit_code == 2


def test_set_prop_unknown_node_exits_1(_isolated_state_dir):
    _seed_simple_graph(_isolated_state_dir)
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--node-id",
            "ghost",
            "--prop",
            "x=1",
        ],
    )
    assert res.exit_code == 1
    assert "IdentityError" in res.output or "IdentityError" in (res.stderr or "")


def test_set_prop_with_schema_validates_type_mismatch_exits_1(_isolated_state_dir):
    _seed_simple_graph(_isolated_state_dir, with_schema=True)
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--node-id",
            "n-a",
            "--prop",
            "age=thirty",
        ],
    )
    assert res.exit_code == 1
    assert "PropertyShapeError" in res.output or "PropertyShapeError" in (
        res.stderr or ""
    )


def test_set_prop_with_schema_accepts_valid_type(_isolated_state_dir):
    _seed_simple_graph(_isolated_state_dir, with_schema=True)
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--node-id",
            "n-a",
            "--prop",
            "age=31",
            "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["properties"]["age"] == 31


def test_set_prop_persists_to_state_file(_isolated_state_dir):
    _seed_simple_graph(_isolated_state_dir)
    runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--node-id",
            "n-a",
            "--prop",
            "city=NYC",
        ],
    )
    raw = (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    state = json.loads(raw)
    n_a = next(n for n in state["nodes"] if n["node_id"] == "n-a")
    assert n_a["properties"] == {"age": 30, "city": "NYC"}


# ── Phase 04 — Pick D + N5: ref:* preservation across --replace ─────────────


def test_replace_preserves_existing_ref_property(_isolated_state_dir):
    """``set-prop --replace`` keeps ``ref:*`` keys even when user doesn't supply them."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "Alice",
            "--name",
            "g1",
            "--type",
            "Person",
            "--node-id",
            "n-a",
            "--prop",
            "age=30",
            "--prop",
            "ref:anchor=anchor-uuid-1",
        ],
    )
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--node-id",
            "n-a",
            "--prop",
            "city=NYC",
            "--replace",
            "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    # ref:anchor SURVIVED the replace; age was DROPPED (not user-supplied).
    assert data["properties"] == {"city": "NYC", "ref:anchor": "anchor-uuid-1"}


def test_replace_user_supplied_ref_overwrites_existing(_isolated_state_dir):
    """User-supplied ``ref:*`` values win on collision with existing refs."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "Alice",
            "--name",
            "g1",
            "--type",
            "Person",
            "--node-id",
            "n-a",
            "--prop",
            "ref:anchor=old-uuid",
        ],
    )
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--node-id",
            "n-a",
            "--prop",
            "ref:anchor=new-uuid",
            "--replace",
            "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["properties"] == {"ref:anchor": "new-uuid"}


def test_replace_preserves_multiple_refs(_isolated_state_dir):
    """Multiple existing refs all survive a replace that doesn't touch them."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "Alice",
            "--name",
            "g1",
            "--type",
            "Person",
            "--node-id",
            "n-a",
            "--prop",
            "ref:anchor=a-uuid",
            "--prop",
            "ref:source=s-uuid",
            "--prop",
            "name=Alice",
        ],
    )
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--node-id",
            "n-a",
            "--prop",
            "city=NYC",
            "--replace",
            "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["properties"] == {
        "city": "NYC",
        "ref:anchor": "a-uuid",
        "ref:source": "s-uuid",
    }


def test_replace_user_partial_ref_overwrite(_isolated_state_dir):
    """User overwrites one ref; the others survive."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "Alice",
            "--name",
            "g1",
            "--type",
            "Person",
            "--node-id",
            "n-a",
            "--prop",
            "ref:anchor=a-uuid",
            "--prop",
            "ref:source=s-uuid",
        ],
    )
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--node-id",
            "n-a",
            "--prop",
            "ref:anchor=new-a",
            "--replace",
            "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["properties"] == {"ref:anchor": "new-a", "ref:source": "s-uuid"}


# ── Phase 04 — NEW1: legacy reserved-key recovery via --replace ─────────────


def test_legacy_node_set_prop_default_merge_fails_on_reserved_key(
    _isolated_state_dir,
):
    """A Phase 03 v=1 file with a reserved-key property fails default merge."""
    # Hand-write a v=1 graph state file with a poisoned property.
    state = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-000000000010",
        "name": "g1",
        "role": None,
        "nodes": [
            {
                "node_id": "n-a",
                "value": "Alice",
                "type_name": "Person",
                "properties": {"id": "evil-legacy", "name": "Alice"},
            }
        ],
        "edges": [],
        "hyperedges": [],
    }
    (_isolated_state_dir / "graph-g1.json").write_text(
        json.dumps(state), encoding="utf-8"
    )
    # Default merge on a non-reserved key still fails because the FULL
    # candidate bag (existing + new) contains the reserved key.
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--node-id",
            "n-a",
            "--prop",
            "city=NYC",
        ],
    )
    assert res.exit_code == 1
    assert "PropertyShapeError" in res.output or "PropertyShapeError" in (
        res.stderr or ""
    )


def test_legacy_node_set_prop_replace_recovers(_isolated_state_dir):
    """``set-prop --replace`` strips reserved keys; recovery path."""
    state = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-000000000011",
        "name": "g1",
        "role": None,
        "nodes": [
            {
                "node_id": "n-a",
                "value": "Alice",
                "type_name": "Person",
                "properties": {"id": "evil-legacy", "name": "Alice"},
            }
        ],
        "edges": [],
        "hyperedges": [],
    }
    (_isolated_state_dir / "graph-g1.json").write_text(
        json.dumps(state), encoding="utf-8"
    )
    res = runner.invoke(
        app,
        [
            "graph",
            "set-prop",
            "--name",
            "g1",
            "--node-id",
            "n-a",
            "--prop",
            "name=Alice",
            "--prop",
            "city=NYC",
            "--replace",
            "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    # Reserved 'id' is gone; non-ref user props applied.
    assert data["properties"] == {"name": "Alice", "city": "NYC"}
