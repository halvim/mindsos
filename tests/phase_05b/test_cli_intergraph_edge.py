"""CLI tests for intergraph-edge subcommands on `mindsos metagraph`.

Covers add-intergraph-edge, remove-intergraph-edge, list-intergraph-edges,
and the 4-way mutex on set-prop (Pushback 27-A).
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def two_graph_metagraph(cli, _isolated_state_dir):
    """Build a metagraph with 2 graphs + 1 node each via CLI."""
    cli("graph", "create", "--name", "lex", "--role", "lexicon")
    cli("graph", "add-node", "cat", "--name", "lex", "--node-id", "n_cat", "--type", "Word")
    cli("graph", "create", "--name", "cpt", "--role", "concepts")
    cli("graph", "add-node", "Cat#1", "--name", "cpt", "--node-id", "n_concept", "--type", "Concept")
    cli("metagraph", "create", "--name", "mg")
    cli("metagraph", "add-graph", "--name", "mg", "--graph", "lex")
    cli("metagraph", "add-graph", "--name", "mg", "--graph", "cpt")


class TestAddIntergraphEdgeCLI:
    def test_happy_path(self, cli, two_graph_metagraph):
        r = cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "EVOKES",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["source_graph"] == "lex"
        assert out["source_node"] == "n_cat"
        assert out["target_graph"] == "cpt"
        assert out["target_node"] == "n_concept"
        assert out["type_name"] == "EVOKES"
        assert out["compositional"] is False

    def test_compositional_flag(self, cli, two_graph_metagraph):
        r = cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "COMPOSED_OF",
            "--compositional",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout)["compositional"] is True

    def test_label_round_trip(self, cli, two_graph_metagraph):
        r = cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "EVOKES", "--label", "primary",
            "--json",
        )
        assert r.returncode == 0
        assert json.loads(r.stdout)["label"] == "primary"

    def test_properties_round_trip(self, cli, two_graph_metagraph):
        r = cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "EVOKES",
            "--prop", "weight=0.5", "--prop", "tag=primary",
            "--json",
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["properties"]["weight"] == 0.5
        assert out["properties"]["tag"] == "primary"

    def test_explicit_edge_id(self, cli, two_graph_metagraph):
        r = cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "EVOKES",
            "--intergraph-edge-id", "my-explicit-id",
            "--json",
        )
        assert r.returncode == 0
        assert json.loads(r.stdout)["edge_id"] == "my-explicit-id"

    def test_self_graph_refused(self, cli, two_graph_metagraph):
        r = cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "lex", "--target-node", "n_cat",
            "--type", "X",
        )
        assert r.returncode == 1
        assert "SchemaError" in r.stderr

    def test_invalid_cypher_type(self, cli, two_graph_metagraph):
        r = cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "lowercase_invalid",
        )
        assert r.returncode == 1
        assert "CypherError" in r.stderr

    def test_missing_source_node(self, cli, two_graph_metagraph):
        r = cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "missing",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "X",
        )
        assert r.returncode == 1
        assert "IdentityError" in r.stderr

    def test_missing_target_node(self, cli, two_graph_metagraph):
        r = cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "missing",
            "--type", "X",
        )
        assert r.returncode == 1


class TestRemoveIntergraphEdgeCLI:
    def test_happy_path(self, cli, two_graph_metagraph):
        r = cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "X",
            "--intergraph-edge-id", "remove_me",
            "--json",
        )
        assert r.returncode == 0
        r = cli(
            "metagraph", "remove-intergraph-edge",
            "--name", "mg",
            "--intergraph-edge-id", "remove_me",
            "--json",
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["removed"] is True
        assert out["intergraph_edge_id"] == "remove_me"

    def test_compositional_refused(self, cli, two_graph_metagraph):
        cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "X",
            "--compositional",
            "--intergraph-edge-id", "comp_id",
        )
        r = cli(
            "metagraph", "remove-intergraph-edge",
            "--name", "mg", "--intergraph-edge-id", "comp_id",
        )
        assert r.returncode == 1
        assert "CompositionalImmutableError" in r.stderr

    def test_unknown_id(self, cli, two_graph_metagraph):
        r = cli(
            "metagraph", "remove-intergraph-edge",
            "--name", "mg", "--intergraph-edge-id", "nonexistent",
        )
        assert r.returncode == 1
        assert "IdentityError" in r.stderr


class TestListIntergraphEdgesCLI:
    def test_empty(self, cli, two_graph_metagraph):
        r = cli("metagraph", "list-intergraph-edges", "--name", "mg", "--json")
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["intergraph_edges"] == []

    def test_with_edges(self, cli, two_graph_metagraph):
        cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "EVOKES",
            "--intergraph-edge-id", "id1",
            "--label", "primary",
        )
        r = cli("metagraph", "list-intergraph-edges", "--name", "mg", "--json")
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert len(out["intergraph_edges"]) == 1
        e = out["intergraph_edges"][0]
        assert e["edge_id"] == "id1"
        assert e["source_graph"] == "lex"
        assert e["target_graph"] == "cpt"
        assert e["type_name"] == "EVOKES"
        assert e["label"] == "primary"

    def test_byte_stable_sort(self, cli, two_graph_metagraph):
        for eid in ("zzz", "aaa", "mmm"):
            cli(
                "metagraph", "add-intergraph-edge",
                "--name", "mg",
                "--source-graph", "lex", "--source-node", "n_cat",
                "--target-graph", "cpt", "--target-node", "n_concept",
                "--type", "X",
                "--intergraph-edge-id", eid,
            )
        r = cli("metagraph", "list-intergraph-edges", "--name", "mg", "--json")
        out = json.loads(r.stdout)
        edge_ids = [e["edge_id"] for e in out["intergraph_edges"]]
        assert edge_ids == ["aaa", "mmm", "zzz"]


class TestSetPropFourWayMutex:
    """Pushback 27-A — set-prop extends from 3-way to 4-way mutex."""

    def test_intergraph_edge_id_target_works(self, cli, two_graph_metagraph):
        cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "X", "--intergraph-edge-id", "ie1",
        )
        r = cli(
            "metagraph", "set-prop",
            "--name", "mg", "--intergraph-edge-id", "ie1",
            "--prop", "k=v", "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["kind"] == "intergraph_edge"
        assert out["properties"]["k"] == "v"

    def test_compositional_set_prop_refused(self, cli, two_graph_metagraph):
        cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "X", "--intergraph-edge-id", "comp",
            "--compositional",
        )
        r = cli(
            "metagraph", "set-prop",
            "--name", "mg", "--intergraph-edge-id", "comp",
            "--prop", "k=v",
        )
        assert r.returncode == 1
        assert "CompositionalImmutableError" in r.stderr

    def test_zero_options_refused(self, cli, two_graph_metagraph):
        r = cli(
            "metagraph", "set-prop",
            "--name", "mg", "--prop", "k=v",
        )
        assert r.returncode == 2
        assert "4-way" in r.stderr or "Pushback" in r.stderr

    def test_two_options_refused(self, cli, two_graph_metagraph):
        r = cli(
            "metagraph", "set-prop",
            "--name", "mg",
            "--on-metagraph", "--intergraph-edge-id", "x",
            "--prop", "k=v",
        )
        assert r.returncode == 2

    def test_replace_works_on_intergraph_edge(self, cli, two_graph_metagraph):
        cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "X", "--intergraph-edge-id", "ie",
            "--prop", "a=1",
        )
        r = cli(
            "metagraph", "set-prop",
            "--name", "mg", "--intergraph-edge-id", "ie",
            "--prop", "b=2", "--replace", "--json",
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["properties"] == {"b": "2"}


class TestInspectIncludesIntergraphEdgesCount:
    def test_inspect_json_shape(self, cli, two_graph_metagraph):
        cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "X",
        )
        r = cli("metagraph", "inspect", "--name", "mg", "--json")
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert "intergraph_edges" in out["counts"]
        assert out["counts"]["intergraph_edges"] == 1
        assert "schema_name" in out
        assert out["schema_name"] is None

    def test_list_json_shape_extends(self, cli, two_graph_metagraph):
        cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "X",
        )
        r = cli("metagraph", "list", "--json")
        assert r.returncode == 0
        out = json.loads(r.stdout)
        mg_entry = next(e for e in out["metagraphs"] if e["name"] == "mg")
        assert mg_entry["intergraph_edges_count"] == 1
        assert "schema_name" in mg_entry
