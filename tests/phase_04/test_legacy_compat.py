"""Phase 04 backward-compatibility tests for Phase 03 v=1 state files.

Locks the contract:

* v=1 graph state files (no ``schema_name`` field) load cleanly under
  Phase 04.
* v=1 graphs with reserved-key or non-primitive properties (Phase 03
  had no ``validate_user_properties`` enforcement) load cleanly via
  ``_validate=False`` rehydration; mutations on those properties surface
  the violation; recovery via ``set-prop --replace``.
* First Phase 04 mutation upgrades the on-disk format from v=1 to v=2
  (one-way migration).
* Corrupt ``PropertyType`` vocab in a schema state file raises
  ``RuntimeError`` → exit 1 with a structured error.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


# ── v=1 → v=2 migration on first mutation (NEW2) ───────────────────────────


def test_phase_03_v1_file_upgrades_to_v2_on_mutation(_isolated_state_dir):
    """First Phase 04 mutation upgrades the file's _state_version 1 → 2."""
    legacy = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-000000000050",
        "name": "g",
        "role": "ontology",
        "nodes": [
            {
                "node_id": "n-a",
                "value": "Alice",
                "type_name": "Person",
                "properties": {"name": "Alice"},
            }
        ],
        "edges": [],
        "hyperedges": [],
    }
    path = _isolated_state_dir / "graph-g.json"
    path.write_text(json.dumps(legacy), encoding="utf-8")
    res = runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "Bob",
            "--name",
            "g",
            "--type",
            "Person",
            "--node-id",
            "n-b",
        ],
    )
    assert res.exit_code == 0, res.output
    raw = json.loads(path.read_text(encoding="utf-8"))
    # Phase 04-v2 — first mutation cumulative-upgrades v=1 → v=3 (jump).
    from mindsos_cli import state as state_mod
    assert raw["_state_version"] == state_mod.GRAPH_STATE_VERSION
    # schema_name field was added (None) on write.
    assert "schema_name" in raw
    assert raw["schema_name"] is None


def test_phase_03_v1_file_inspect_does_not_upgrade(_isolated_state_dir):
    """``inspect`` is read-only — does NOT trigger the v=1 → v=2 upgrade."""
    legacy = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-000000000051",
        "name": "g",
        "role": None,
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    path = _isolated_state_dir / "graph-g.json"
    path.write_text(json.dumps(legacy), encoding="utf-8")
    res = runner.invoke(app, ["graph", "inspect", "--name", "g", "--json"])
    assert res.exit_code == 0
    raw = json.loads(path.read_text(encoding="utf-8"))
    # File is unchanged after inspect.
    assert raw["_state_version"] == 1


# ── Legacy reserved-key tolerance on load (NEW1) ───────────────────────────


def test_legacy_v1_with_reserved_key_loads(_isolated_state_dir):
    """A Phase 03 graph with a reserved 'id' key in node properties loads."""
    legacy = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-000000000052",
        "name": "g",
        "role": None,
        "nodes": [
            {
                "node_id": "n-a",
                "value": "Alice",
                "type_name": "Person",
                "properties": {"id": "evil", "name": "Alice"},
            }
        ],
        "edges": [],
        "hyperedges": [],
    }
    (_isolated_state_dir / "graph-g.json").write_text(
        json.dumps(legacy), encoding="utf-8"
    )
    # inspect succeeds — rehydration tolerates the reserved key.
    res = runner.invoke(app, ["graph", "inspect", "--name", "g", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["counts"]["nodes"] == 1


def test_legacy_v1_with_non_primitive_property_loads(_isolated_state_dir):
    """Non-primitive property values (e.g. mixed list) don't block load."""
    legacy = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-000000000053",
        "name": "g",
        "role": None,
        "nodes": [
            {
                "node_id": "n-a",
                "value": "Alice",
                "type_name": "Person",
                "properties": {"tags": [1, "mixed"]},  # mixed list
            }
        ],
        "edges": [],
        "hyperedges": [],
    }
    (_isolated_state_dir / "graph-g.json").write_text(
        json.dumps(legacy), encoding="utf-8"
    )
    res = runner.invoke(app, ["graph", "inspect", "--name", "g", "--json"])
    assert res.exit_code == 0


def test_legacy_v1_fresh_add_node_validates(_isolated_state_dir):
    """A fresh add-node call DOES validate — only rehydration tolerates legacy."""
    legacy = {
        "_state_version": 1,
        "graph_id": "00000000-0000-4000-8000-000000000054",
        "name": "g",
        "role": None,
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    (_isolated_state_dir / "graph-g.json").write_text(
        json.dumps(legacy), encoding="utf-8"
    )
    # Adding a NEW node with a reserved key fails.
    res = runner.invoke(
        app,
        [
            "graph",
            "add-node",
            "Bob",
            "--name",
            "g",
            "--type",
            "Person",
            "--prop",
            "id=evil",
        ],
    )
    assert res.exit_code == 1
    assert "PropertyShapeError" in res.output or "PropertyShapeError" in (
        res.stderr or ""
    )


# ── Corrupt PropertyType in schema state file (NEW2) ──────────────────────


def test_corrupt_property_type_in_schema_state_exits_1(_isolated_state_dir):
    """A schema state file with an unrecognised PropertyType vocab exits 1."""
    corrupt = {
        "_state_version": 1,
        "name": "s1",
        "strict": True,
        "node_types": [
            {
                "name": "Person",
                "property_types": {"age": "uint32"},  # not in vocab
                "description": None,
            }
        ],
        "edge_types": [],
    }
    (_isolated_state_dir / "schema-s1.json").write_text(
        json.dumps(corrupt), encoding="utf-8"
    )
    res = runner.invoke(app, ["schema", "inspect", "--name", "s1"])
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "uint32" in output
    assert "unrecognised PropertyType" in output or "Valid:" in output


def test_corrupt_property_type_in_edge_type_exits_1(_isolated_state_dir):
    """Same check for edge type property_types."""
    corrupt = {
        "_state_version": 1,
        "name": "s1",
        "strict": True,
        "node_types": [
            {"name": "Person", "property_types": {}, "description": None},
            {"name": "Org", "property_types": {}, "description": None},
        ],
        "edge_types": [
            {
                "name": "WORKS_AT",
                "allowed_sources": ["Person"],
                "allowed_targets": ["Org"],
                "property_types": {"since": "datetime"},  # not in vocab
                "description": None,
            }
        ],
    }
    (_isolated_state_dir / "schema-s1.json").write_text(
        json.dumps(corrupt), encoding="utf-8"
    )
    res = runner.invoke(app, ["schema", "inspect", "--name", "s1"])
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "datetime" in output
