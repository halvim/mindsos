"""Tier 7 — CLI ``mindsos schema migrate-check`` verb.

Covers mutex flag handling, exit codes (PB-15), and per-Graph end-to-end
through the state-file rehydration path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindsos_cli.commands.schema import schema_app


_runner = CliRunner()


def _write_minimal_schema_state(path: Path, *, name: str, node_types=None,
                                edge_types=None) -> None:
    """Write a Phase 04-v2 schema state-file (v=2) at ``path``."""
    path.write_text(json.dumps({
        "_state_version": 2,
        "name": name,
        "strict": True,
        "node_types": node_types or [],
        "edge_types": edge_types or [],
        "hyperedge_types": [],
    }, indent=2))


def _write_minimal_graph_state(path: Path, *, name: str,
                               nodes=None, edges=None) -> None:
    """Write a Phase 10 graph state-file (v=5) at ``path``."""
    path.write_text(json.dumps({
        "_state_version": 5,
        "graph_id": f"gid-{name}",
        "name": name,
        "role": None,
        "schema_name": None,
        "metagraph_name": None,
        "nodes": nodes or [],
        "edges": edges or [],
        "hyperedges": [],
    }, indent=2))


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    """Isolated state dir for the CLI to read/write under."""
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(tmp_path))
    return tmp_path


# ── mutex + usage validation ────────────────────────────────────────────────


def test_old_and_old_file_mutex(state_dir) -> None:
    """Specifying both --old and --old-file → exit 2."""
    result = _runner.invoke(schema_app, [
        "migrate-check",
        "--old", "v1", "--old-file", "/tmp/x.json",
        "--graph", "g",
    ])
    assert result.exit_code == 2
    assert "old" in result.stdout.lower() or "old" in (result.stderr or "").lower()


def test_neither_old_nor_old_file_rejected(state_dir) -> None:
    """Specifying neither → exit 2."""
    result = _runner.invoke(schema_app, [
        "migrate-check",
        "--graph", "g",
    ])
    assert result.exit_code == 2


def test_graph_and_metagraph_mutex(state_dir) -> None:
    """Specifying both --graph and --metagraph → exit 2."""
    result = _runner.invoke(schema_app, [
        "migrate-check",
        "--old-file", "/tmp/x.json",
        "--graph", "g", "--metagraph", "m",
    ])
    assert result.exit_code == 2


def test_neither_graph_nor_metagraph_rejected(state_dir) -> None:
    """Specifying neither → exit 2."""
    result = _runner.invoke(schema_app, [
        "migrate-check",
        "--old-file", "/tmp/x.json",
    ])
    assert result.exit_code == 2


def test_invalid_detail_value_rejected(state_dir) -> None:
    """``--detail`` other than summary/each → exit 2."""
    result = _runner.invoke(schema_app, [
        "migrate-check",
        "--old-file", "/tmp/x.json",
        "--graph", "g",
        "--detail", "bogus",
    ])
    assert result.exit_code == 2


def test_missing_old_file_path_exits_1(state_dir, tmp_path) -> None:
    """Non-existent ``--old-file`` exits 1."""
    result = _runner.invoke(schema_app, [
        "migrate-check",
        "--old-file", str(tmp_path / "does_not_exist.json"),
        "--graph", "g",
    ])
    assert result.exit_code == 1


# ── happy path: graph mode with violations ──────────────────────────────────


def test_graph_mode_clean_scan_exits_0(state_dir, tmp_path) -> None:
    """Graph + matching schemas → 0 violations + exit 0."""
    # Old + new identical schema; graph data conforms.
    _write_minimal_schema_state(
        state_dir / "schema-v1.json", name="v1",
        node_types=[{"name": "Person", "property_types": {}, "description": None}],
        edge_types=[],
    )
    _write_minimal_graph_state(
        state_dir / "graph-g1.json", name="g1",
        nodes=[
            {"id": "alice", "type_name": "Person", "value": None,
             "properties": {}, "_version": 1},
        ],
    )
    result = _runner.invoke(schema_app, [
        "migrate-check",
        "--old", "v1", "--new", "v1",
        "--graph", "g1",
        "--detail", "summary", "--json",
    ])
    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    payload = json.loads(result.stdout)
    assert payload["violation_count"] == 0


def test_graph_mode_violations_default_exit_1(state_dir, tmp_path) -> None:
    """Violations + default → exit 1."""
    _write_minimal_schema_state(
        state_dir / "schema-v1.json", name="v1",
        node_types=[{"name": "Person", "property_types": {}, "description": None}],
        edge_types=[],
    )
    _write_minimal_schema_state(
        state_dir / "schema-v2.json", name="v2",
        node_types=[],  # Person removed.
        edge_types=[],
    )
    _write_minimal_graph_state(
        state_dir / "graph-g1.json", name="g1",
        nodes=[
            {"id": "alice", "type_name": "Person", "value": None,
             "properties": {}, "_version": 1},
        ],
    )
    result = _runner.invoke(schema_app, [
        "migrate-check",
        "--old", "v1", "--new", "v2",
        "--graph", "g1",
        "--detail", "summary", "--json",
    ])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["violation_count"] >= 1
    assert any(v["kind"] == "removed_node_type" for v in payload["violations"])


def test_graph_mode_violations_with_exit_zero_exits_0(state_dir, tmp_path) -> None:
    """``--exit-zero`` overrides exit-1-on-violations (PB-15)."""
    _write_minimal_schema_state(
        state_dir / "schema-v1.json", name="v1",
        node_types=[{"name": "Person", "property_types": {}, "description": None}],
        edge_types=[],
    )
    _write_minimal_schema_state(
        state_dir / "schema-v2.json", name="v2",
        node_types=[],
        edge_types=[],
    )
    _write_minimal_graph_state(
        state_dir / "graph-g1.json", name="g1",
        nodes=[
            {"id": "alice", "type_name": "Person", "value": None,
             "properties": {}, "_version": 1},
        ],
    )
    result = _runner.invoke(schema_app, [
        "migrate-check",
        "--old", "v1", "--new", "v2",
        "--graph", "g1",
        "--exit-zero", "--json",
    ])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["violation_count"] >= 1


def test_json_output_payload_carries_schema_and_scope(state_dir, tmp_path) -> None:
    """JSON payload includes schema, scope, detail, violations array."""
    _write_minimal_schema_state(
        state_dir / "schema-v1.json", name="v1",
        node_types=[{"name": "Person", "property_types": {}, "description": None}],
        edge_types=[],
    )
    _write_minimal_graph_state(
        state_dir / "graph-g1.json", name="g1",
        nodes=[],
    )
    result = _runner.invoke(schema_app, [
        "migrate-check",
        "--old", "v1", "--new", "v1",
        "--graph", "g1",
        "--json",
    ])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema"]["old"] == "v1"
    assert payload["schema"]["new"] == "v1"
    assert payload["scope"]["graph"] == "g1"
    assert payload["scope"]["metagraph"] is None
    assert payload["detail"] == "summary"
    assert "violations" in payload
    assert "violation_count" in payload
