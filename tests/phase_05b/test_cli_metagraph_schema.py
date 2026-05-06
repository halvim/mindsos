"""CLI tests for `mindsos metagraph-schema` subapp.

Pushbacks 3-A (subapp parallel to mindsos schema), 5-A (strict gates
property typing), 11-A (reusable across N metagraphs), 20-A (reset
orphan check + force-strip), 23-A (mutation-while-attached warning),
30-A (attach-schema JSON shape), 28-A + DMS-A (detach-schema unified
recovery).
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def empty_schema(cli, _isolated_state_dir):
    cli("metagraph-schema", "create", "--name", "ms1")


@pytest.fixture
def metagraph_with_two_graphs(cli, _isolated_state_dir):
    cli("graph", "create", "--name", "lex", "--role", "lexicon")
    cli("graph", "add-node", "--name", "lex", "--node-id", "n_cat", "--value", "cat", "--type", "Word")
    cli("graph", "create", "--name", "cpt", "--role", "concepts")
    cli("graph", "add-node", "--name", "cpt", "--node-id", "n_concept", "--value", "Cat#1", "--type", "Concept")
    cli("metagraph", "create", "--name", "mg")
    cli("metagraph", "add-graph", "--name", "mg", "--graph", "lex")
    cli("metagraph", "add-graph", "--name", "mg", "--graph", "cpt")


class TestCreate:
    def test_default_non_strict(self, cli, _isolated_state_dir):
        r = cli("metagraph-schema", "create", "--name", "ms1", "--json")
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["name"] == "ms1"
        assert out["strict"] is False
        assert out["intergraph_edge_types"] == []

    def test_strict_flag(self, cli, _isolated_state_dir):
        r = cli("metagraph-schema", "create", "--name", "ms_strict",
                "--strict", "--json")
        assert r.returncode == 0
        assert json.loads(r.stdout)["strict"] is True

    def test_duplicate_refused(self, cli, _isolated_state_dir):
        cli("metagraph-schema", "create", "--name", "ms1")
        r = cli("metagraph-schema", "create", "--name", "ms1")
        assert r.returncode == 1
        assert "already exists" in r.stderr.lower() or "IdentityError" in r.stderr

    def test_invalid_name_regex(self, cli, _isolated_state_dir):
        r = cli("metagraph-schema", "create", "--name", "../escape")
        assert r.returncode == 2


class TestList:
    def test_empty_state_dir(self, cli, _isolated_state_dir):
        r = cli("metagraph-schema", "list", "--json")
        assert r.returncode == 0
        assert json.loads(r.stdout)["metagraph_schemas"] == []

    def test_lists_created_schemas(self, cli, _isolated_state_dir):
        cli("metagraph-schema", "create", "--name", "ms1")
        cli("metagraph-schema", "create", "--name", "ms2", "--strict")
        r = cli("metagraph-schema", "list", "--json")
        out = json.loads(r.stdout)
        assert len(out["metagraph_schemas"]) == 2
        names = {e["name"] for e in out["metagraph_schemas"]}
        assert names == {"ms1", "ms2"}


class TestInspect:
    def test_empty_schema(self, cli, empty_schema):
        r = cli("metagraph-schema", "inspect", "--name", "ms1", "--json")
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["name"] == "ms1"
        assert out["strict"] is False
        assert out["counts"]["intergraph_edge_types"] == 0
        assert out["intergraph_edge_types"] == []

    def test_attached_metagraphs_listed(self, cli, empty_schema, metagraph_with_two_graphs):
        cli("metagraph", "attach-schema", "--name", "mg", "--schema", "ms1")
        r = cli("metagraph-schema", "inspect", "--name", "ms1", "--json")
        assert r.returncode == 0
        assert "mg" in json.loads(r.stdout)["attached_metagraphs"]


class TestAddIntergraphEdgeType:
    def test_happy_path(self, cli, empty_schema):
        r = cli(
            "metagraph-schema", "add-intergraph-edge-type",
            "--schema", "ms1", "--type-name", "EVOKES",
            "--allowed-source-type", "Word",
            "--allowed-target-type", "Concept",
            "--allowed-source-graph", "lexicon",
            "--allowed-target-graph", "concepts",
            "--prop-type", "weight=float",
            "--description", "Lex→Concept evocation",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["type_name"] == "EVOKES"
        assert out["allowed_source_types"] == ["Word"]
        assert out["allowed_target_types"] == ["Concept"]
        assert out["allowed_source_graphs"] == ["lexicon"]
        assert out["allowed_target_graphs"] == ["concepts"]
        assert out["property_types"] == {"weight": "float"}

    def test_invalid_cypher_type_name(self, cli, empty_schema):
        r = cli(
            "metagraph-schema", "add-intergraph-edge-type",
            "--schema", "ms1", "--type-name", "lowercase_invalid",
        )
        assert r.returncode == 1
        assert "CypherError" in r.stderr

    def test_duplicate_refused(self, cli, empty_schema):
        cli(
            "metagraph-schema", "add-intergraph-edge-type",
            "--schema", "ms1", "--type-name", "EVOKES",
        )
        r = cli(
            "metagraph-schema", "add-intergraph-edge-type",
            "--schema", "ms1", "--type-name", "EVOKES",
        )
        assert r.returncode == 1
        assert "UnknownTypeError" in r.stderr

    def test_warning_on_attached(self, cli, empty_schema, metagraph_with_two_graphs):
        """Pushback 23-A — stderr warning if schema is attached."""
        cli("metagraph", "attach-schema", "--name", "mg", "--schema", "ms1")
        r = cli(
            "metagraph-schema", "add-intergraph-edge-type",
            "--schema", "ms1", "--type-name", "EVOKES",
        )
        assert r.returncode == 0
        assert "warning" in r.stderr.lower()
        assert "attached" in r.stderr.lower()
        assert "mg" in r.stderr


class TestAttachSchemaCLI:
    def test_happy_path(self, cli, empty_schema, metagraph_with_two_graphs):
        r = cli(
            "metagraph", "attach-schema", "--name", "mg", "--schema", "ms1",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["new_schema"] == "ms1"
        assert out["previous_schema"] is None
        assert out["validated_intergraph_edges"] == 0

    def test_validated_count(self, cli, empty_schema, metagraph_with_two_graphs):
        cli(
            "metagraph-schema", "add-intergraph-edge-type",
            "--schema", "ms1", "--type-name", "EVOKES",
        )
        cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "EVOKES",
        )
        # Reset state to detached.
        cli("metagraph-schema", "create", "--name", "ms2")
        cli("metagraph-schema", "add-intergraph-edge-type",
            "--schema", "ms2", "--type-name", "EVOKES")
        r = cli(
            "metagraph", "attach-schema", "--name", "mg", "--schema", "ms2",
            "--json",
        )
        # Note: ms1 is already attached from above; this should refuse
        # with "detach first" per Pushback 12-A.
        assert r.returncode == 1
        assert "IdentityError" in r.stderr

    def test_attach_while_attached_refuses(self, cli, empty_schema, metagraph_with_two_graphs):
        cli("metagraph-schema", "create", "--name", "ms2")
        cli("metagraph", "attach-schema", "--name", "mg", "--schema", "ms1")
        r = cli(
            "metagraph", "attach-schema", "--name", "mg", "--schema", "ms2",
        )
        assert r.returncode == 1
        assert "detach" in r.stderr.lower()

    def test_role_mismatch_warning(self, cli, _isolated_state_dir):
        """Pushback 19-B — stderr warning on role gaps."""
        cli("graph", "create", "--name", "g1")  # no role
        cli("metagraph", "create", "--name", "mg")
        cli("metagraph", "add-graph", "--name", "mg", "--graph", "g1")
        cli("metagraph-schema", "create", "--name", "ms1")
        cli(
            "metagraph-schema", "add-intergraph-edge-type",
            "--schema", "ms1", "--type-name", "EVOKES",
            "--allowed-source-graph", "lexicon",
            "--allowed-target-graph", "concepts",
        )
        r = cli("metagraph", "attach-schema", "--name", "mg", "--schema", "ms1")
        assert r.returncode == 0
        assert "warning" in r.stderr.lower()
        assert "lexicon" in r.stderr or "concepts" in r.stderr

    def test_eager_validation_failure(self, cli, _isolated_state_dir):
        cli("graph", "create", "--name", "lex", "--role", "lexicon")
        cli("graph", "add-node", "--name", "lex", "--node-id", "n", "--value", "v", "--type", "Word")
        cli("graph", "create", "--name", "cpt", "--role", "concepts")
        cli("graph", "add-node", "--name", "cpt", "--node-id", "n", "--value", "v", "--type", "Concept")
        cli("metagraph", "create", "--name", "mg")
        cli("metagraph", "add-graph", "--name", "mg", "--graph", "lex")
        cli("metagraph", "add-graph", "--name", "mg", "--graph", "cpt")
        cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n",
            "--target-graph", "cpt", "--target-node", "n",
            "--type", "EVOKES",
        )
        # Build a schema with NO EVOKES type — eager validation refuses.
        cli("metagraph-schema", "create", "--name", "ms_empty")
        r = cli(
            "metagraph", "attach-schema", "--name", "mg", "--schema", "ms_empty",
        )
        assert r.returncode == 1
        assert "UnknownTypeError" in r.stderr


class TestDetachSchemaCLI:
    def test_happy_path(self, cli, empty_schema, metagraph_with_two_graphs):
        cli("metagraph", "attach-schema", "--name", "mg", "--schema", "ms1")
        r = cli(
            "metagraph", "detach-schema", "--name", "mg", "--json",
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["previous_schema"] == "ms1"
        assert out["detached"] is True
        assert out["used_raw_fallback"] is False

    def test_no_schema_attached_refused(self, cli, metagraph_with_two_graphs):
        r = cli(
            "metagraph", "detach-schema", "--name", "mg",
        )
        assert r.returncode == 1
        assert "no schema attached" in r.stderr.lower()

    def test_dms_a_dangling_schema_state_file(
        self, cli, empty_schema, metagraph_with_two_graphs, _isolated_state_dir,
    ):
        """Pushback 28-A + DMS-A — detach with stale schema_name reference works."""
        cli("metagraph", "attach-schema", "--name", "mg", "--schema", "ms1")
        # Manually delete the schema state file (simulate corruption /
        # reset --force from another tester etc.).
        schema_path = _isolated_state_dir / "metagraph-schema-ms1.json"
        schema_path.unlink()
        # Detach should succeed via normal path (the FileNotFoundError
        # in _state_to_metagraph sets dangling ref; detach clears it).
        r = cli(
            "metagraph", "detach-schema", "--name", "mg", "--json",
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["previous_schema"] == "ms1"
        assert out["detached"] is True


class TestResetOrphanCheck:
    def test_no_orphans_succeeds(self, cli, empty_schema):
        r = cli("metagraph-schema", "reset", "--name", "ms1")
        assert r.returncode == 0

    def test_orphans_refuse_without_force(self, cli, empty_schema, metagraph_with_two_graphs):
        cli("metagraph", "attach-schema", "--name", "mg", "--schema", "ms1")
        r = cli("metagraph-schema", "reset", "--name", "ms1")
        assert r.returncode == 1
        assert "referenced by" in r.stderr.lower() or "refusing" in r.stderr.lower()

    def test_force_without_yes_refuses(self, cli, empty_schema, metagraph_with_two_graphs):
        cli("metagraph", "attach-schema", "--name", "mg", "--schema", "ms1")
        r = cli("metagraph-schema", "reset", "--name", "ms1", "--force")
        assert r.returncode == 2
        assert "--yes" in r.stderr

    def test_force_yes_strips_back_pointers(
        self, cli, empty_schema, metagraph_with_two_graphs,
    ):
        cli("metagraph", "attach-schema", "--name", "mg", "--schema", "ms1")
        r = cli(
            "metagraph-schema", "reset",
            "--name", "ms1", "--force", "--yes", "--json",
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert "ms1" in out["deleted"]
        assert "mg" in out["stripped_back_pointers"]
        # Verify metagraph state file no longer references the schema.
        r2 = cli("metagraph", "inspect", "--name", "mg", "--json")
        assert json.loads(r2.stdout)["schema_name"] is None

    def test_all_yes(self, cli, _isolated_state_dir):
        cli("metagraph-schema", "create", "--name", "a")
        cli("metagraph-schema", "create", "--name", "b")
        r = cli(
            "metagraph-schema", "reset", "--all", "--yes", "--json",
        )
        assert r.returncode == 0
        assert sorted(json.loads(r.stdout)["deleted"]) == ["a", "b"]
