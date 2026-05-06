"""DMS-A unified detach-schema recovery tests (Pushback 28-A).

Two failure modes the unified detach-schema command handles:
1. Schema state file missing (FileNotFoundError in _state_to_metagraph
   → dangling schema_name set; normal-path detach clears it).
2. Schema state file malformed (RuntimeError → raw-JSON fallback).
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def schema_attached(cli, _isolated_state_dir):
    """Build a metagraph with a schema attached, ready for stale-recovery tests."""
    cli("graph", "create", "--name", "lex", "--role", "lexicon")
    cli("graph", "add-node", "v", "--name", "lex", "--node-id", "n", "--type", "Word")
    cli("graph", "create", "--name", "cpt", "--role", "concepts")
    cli("graph", "add-node", "v", "--name", "cpt", "--node-id", "n", "--type", "Concept")
    cli("metagraph", "create", "--name", "mg")
    cli("metagraph", "add-graph", "--name", "mg", "--graph", "lex")
    cli("metagraph", "add-graph", "--name", "mg", "--graph", "cpt")
    cli("metagraph-schema", "create", "--name", "ms1")
    cli("metagraph", "attach-schema", "--name", "mg", "--schema", "ms1")
    return _isolated_state_dir


class TestDMS_A_StaleSchemaRecovery:
    def test_normal_detach_works_when_schema_intact(self, cli, schema_attached):
        r = cli("metagraph", "detach-schema", "--name", "mg", "--json")
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["used_raw_fallback"] is False
        assert out["previous_schema"] == "ms1"

    def test_dms_a_schema_missing_normal_path_handles(self, cli, schema_attached):
        """Schema file missing — _state_to_metagraph sets dangling ref;
        normal-path detach clears it without the raw fallback."""
        schema_path = schema_attached / "metagraph-schema-ms1.json"
        schema_path.unlink()
        r = cli("metagraph", "detach-schema", "--name", "mg", "--json")
        assert r.returncode == 0
        out = json.loads(r.stdout)
        # Either path acceptable; both clear the reference.
        assert out["previous_schema"] == "ms1"
        assert out["detached"] is True

    def test_dms_a_schema_malformed_raw_fallback(self, cli, schema_attached):
        """Schema file malformed (bad PropertyType vocab) — raw fallback fires."""
        schema_path = schema_attached / "metagraph-schema-ms1.json"
        # Inject a malformed PropertyType.value.
        schema_path.write_text(json.dumps({
            "_state_version": 1,
            "name": "ms1",
            "strict": False,
            "intergraph_edge_types": [
                {
                    "name": "EVOKES",
                    "allowed_source_types": [],
                    "allowed_target_types": [],
                    "allowed_source_graphs": [],
                    "allowed_target_graphs": [],
                    "property_types": {"weight": "INVALID_PROPERTY_TYPE"},
                    "description": None,
                }
            ],
        }))
        r = cli("metagraph", "detach-schema", "--name", "mg", "--json")
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["used_raw_fallback"] is True
        assert out["previous_schema"] == "ms1"
        # Metagraph state file no longer references the schema.
        mg_path = schema_attached / "metagraph-mg.json"
        mg_state = json.loads(mg_path.read_text())
        assert mg_state["schema_name"] is None

    def test_no_schema_attached_refuses(self, cli, _isolated_state_dir):
        cli("metagraph", "create", "--name", "mg_only")
        r = cli("metagraph", "detach-schema", "--name", "mg_only")
        assert r.returncode == 1
        assert "no schema" in r.stderr.lower()

    def test_metagraph_not_found(self, cli, _isolated_state_dir):
        r = cli("metagraph", "detach-schema", "--name", "missing")
        assert r.returncode == 1
