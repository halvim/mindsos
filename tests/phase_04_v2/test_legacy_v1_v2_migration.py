"""Phase 04-v2 — cumulative migration: v=1 ∪ v=2 → v=3 (one-way).

Pre-v=3 hyperedges receive `type_name="UNSPECIFIED"` (SENT-1) on first
read; first mutation upgrades file to v=3.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli import state as state_mod
from mindsos_cli.app import app


runner = CliRunner()


def test_v1_graph_with_hyperedge_loads_with_unspecified_sentinel(_isolated_state_dir):
    """v=1 graph (no schema_name, no hyperedge type_name) loads cleanly."""
    legacy = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-100000000001",
        "name": "g",
        "role": None,
        "nodes": [
            {"node_id": "n-a", "value": "Alice", "type_name": "Person", "properties": {}},
            {"node_id": "n-b", "value": "Bob", "type_name": "Person", "properties": {}},
        ],
        "edges": [],
        "hyperedges": [
            {"edge_id": "he-1", "member_ids": ["n-a", "n-b"], "label": None,
             "properties": {}}
        ],
    }
    (_isolated_state_dir / "graph-g.json").write_text(
        json.dumps(legacy), encoding="utf-8"
    )
    res = runner.invoke(app, ["graph", "list-hyperedges", "--name", "g", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data[0]["type_name"] == "UNSPECIFIED"  # SENT-1 sentinel.


def test_v2_graph_with_hyperedge_loads_with_unspecified_sentinel(_isolated_state_dir):
    """v=2 graph (Phase 04 era, no hyperedge type_name) loads cleanly."""
    legacy = {
        "_state_version": 2,
        "graph_id": "00000000-0000-4000-8000-100000000002",
        "name": "g",
        "role": None,
        "schema_name": None,
        "nodes": [
            {"node_id": "n-a", "value": "Alice", "type_name": "Person", "properties": {}},
        ],
        "edges": [],
        "hyperedges": [
            {"edge_id": "he-1", "member_ids": ["n-a"], "label": "solo",
             "properties": {}}
        ],
    }
    (_isolated_state_dir / "graph-g.json").write_text(
        json.dumps(legacy), encoding="utf-8"
    )
    res = runner.invoke(app, ["graph", "list-hyperedges", "--name", "g", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data[0]["type_name"] == "UNSPECIFIED"


def test_v1_graph_first_mutation_upgrades_to_v3(_isolated_state_dir):
    """First Phase 04-v2 mutation upgrades the file directly v=1 → v=3."""
    legacy = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-100000000003",
        "name": "g",
        "role": None,
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    path = _isolated_state_dir / "graph-g.json"
    path.write_text(json.dumps(legacy), encoding="utf-8")
    res = runner.invoke(
        app,
        ["graph", "add-node", "Bob", "--name", "g", "--type", "Person",
         "--node-id", "n-b"],
    )
    assert res.exit_code == 0
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["_state_version"] == state_mod.GRAPH_STATE_VERSION  # = 3.


def test_v1_schema_loads_as_empty_hyperedge_types(_isolated_state_dir):
    """Phase 04 v=1 schema state file (no hyperedge_types field) loads."""
    legacy = {
        "_state_version": 1,
        "name": "s1",
        "strict": False,
        "node_types": [
            {"name": "Person", "property_types": {}, "description": None}
        ],
        "edge_types": [],
    }
    (_isolated_state_dir / "schema-s1.json").write_text(
        json.dumps(legacy), encoding="utf-8"
    )
    res = runner.invoke(app, ["schema", "inspect", "--name", "s1", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    # hyperedge_types treated as empty list under v=1 schema backward-compat.
    assert data["hyperedge_types"] == []
