"""CLI tests for intergraph-hyperedge subcommands on ``mindsos metagraph`` (Phase 05c).

Covers (P14-A 16-step + P4-A paired-flags + P10-C replace-only update +
P19-A cardinality collapse refusal + P8-A compositional+ordered refusal +
the 5-way set-prop mutex extension + P12-A schema-mutation footgun
warning + P31 P13-B workaround regression coverage on the binary primitive).

These tests SUBPROCESS the installed ``mindsos`` binary (in-container
Python 3.12 + typer); reserved for in-container runs per
``feedback_docker_compose_invocation.md``.
"""

from __future__ import annotations

import json

import pytest


# ─── fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def hyperedge_metagraph(cli, _isolated_state_dir):
    """Build a metagraph with word + letter graphs (cat=c+a+t fixture).

    word graph: role="word", node "cat" (type=Word).
    letter graph: role="letter", nodes "c" / "a" / "t" / "r" / "e" /
    "l" / "o" / "g" / "d" (type=Letter).
    """
    cli("graph", "create", "--name", "word", "--role", "word")
    cli("graph", "add-node", "cat", "--name", "word", "--node-id", "cat", "--type", "Word")
    cli("graph", "add-node", "dog", "--name", "word", "--node-id", "dog", "--type", "Word")
    cli("graph", "create", "--name", "letter", "--role", "letter")
    for ch in ("c", "a", "t", "r", "e", "l", "o", "g", "d"):
        cli(
            "graph", "add-node", ch,
            "--name", "letter", "--node-id", ch, "--type", "Letter",
        )
    cli("metagraph", "create", "--name", "mg")
    cli("metagraph", "add-graph", "--name", "mg", "--graph", "word")
    cli("metagraph", "add-graph", "--name", "mg", "--graph", "letter")


# ─── add-intergraph-hyperedge ──────────────────────────────────────────────


class TestAddIntergraphHyperedgeCLI:
    def test_happy_path_one_anchor_three_members(self, cli, hyperedge_metagraph):
        r = cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--member-graph", "letter", "--member-node", "t",
            "--type", "COMPOSED_OF",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["anchors"] == [["word", "cat"]]
        assert out["members"] == [
            ["letter", "c"], ["letter", "a"], ["letter", "t"],
        ]
        assert out["type_name"] == "COMPOSED_OF"
        assert out["compositional"] is False

    def test_compositional_flag(self, cli, hyperedge_metagraph):
        r = cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--type", "COMPOSED_OF",
            "--compositional",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout)["compositional"] is True

    def test_paired_flags_index_pairing(self, cli, hyperedge_metagraph):
        # P4-A — pair --anchor-graph[i] with --anchor-node[i]. Two
        # anchors + two members; verify pairing reflected in output.
        r = cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--anchor-graph", "word", "--anchor-node", "dog",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--type", "RELATES",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["anchors"] == [["word", "cat"], ["word", "dog"]]

    def test_p4a_mismatched_anchor_count_refused(self, cli, hyperedge_metagraph):
        # P4-A — 2 --anchor-graph + 1 --anchor-node refused at exit 2.
        r = cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-graph", "word",
            "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--type", "T",
            "--json",
        )
        assert r.returncode == 2
        assert "P4-A" in r.stderr
        assert "anchor" in r.stderr

    def test_p4a_mismatched_member_count_refused(self, cli, hyperedge_metagraph):
        r = cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-graph", "letter",
            "--member-node", "c",
            "--type", "T",
            "--json",
        )
        assert r.returncode == 2
        assert "member" in r.stderr

    def test_one_to_one_refused(self, cli, hyperedge_metagraph):
        # NOT 1-to-1 cardinality.
        r = cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--type", "T",
            "--json",
        )
        assert r.returncode == 1
        assert "NOT 1-to-1" in r.stderr or "1-1" in r.stderr.lower()

    def test_overlap_refused(self, cli, hyperedge_metagraph):
        # anchor-member overlap.
        r = cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "letter", "--anchor-node", "c",
            "--anchor-graph", "letter", "--anchor-node", "a",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "t",
            "--type", "T",
            "--json",
        )
        assert r.returncode == 1
        assert "overlap" in r.stderr.lower()

    def test_label_and_properties_round_trip(self, cli, hyperedge_metagraph):
        r = cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--type", "COMPOSED_OF",
            "--label", "cat-comp",
            "--prop", "weight=0.7",
            "--json",
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["label"] == "cat-comp"
        assert out["properties"] == {"weight": 0.7}

    def test_intergraph_hyperedge_id_override(self, cli, hyperedge_metagraph):
        r = cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--type", "T",
            "--intergraph-hyperedge-id", "ihe-custom",
            "--json",
        )
        assert r.returncode == 0
        assert json.loads(r.stdout)["intergraph_hyperedge_id"] == "ihe-custom"

    def test_lowercase_type_refused(self, cli, hyperedge_metagraph):
        r = cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--type", "lowercase",
            "--json",
        )
        assert r.returncode == 1
        assert "Cypher" in r.stderr or "regex" in r.stderr.lower()


# ─── remove-intergraph-hyperedge ───────────────────────────────────────────


class TestRemoveIntergraphHyperedgeCLI:
    def test_happy_remove(self, cli, hyperedge_metagraph):
        r = cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--type", "T",
            "--intergraph-hyperedge-id", "ih1",
            "--json",
        )
        assert r.returncode == 0
        r = cli(
            "metagraph", "remove-intergraph-hyperedge",
            "--name", "mg",
            "--intergraph-hyperedge-id", "ih1",
            "--json",
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["removed"] is True

    def test_remove_compositional_refused(self, cli, hyperedge_metagraph):
        cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--type", "COMPOSED_OF",
            "--compositional",
            "--intergraph-hyperedge-id", "comp1",
            "--json",
        )
        r = cli(
            "metagraph", "remove-intergraph-hyperedge",
            "--name", "mg",
            "--intergraph-hyperedge-id", "comp1",
            "--json",
        )
        assert r.returncode == 1
        assert "Compositional" in r.stderr

    def test_unknown_id_refused(self, cli, hyperedge_metagraph):
        r = cli(
            "metagraph", "remove-intergraph-hyperedge",
            "--name", "mg",
            "--intergraph-hyperedge-id", "nonexistent",
            "--json",
        )
        assert r.returncode == 1
        assert "Identity" in r.stderr or "Unknown" in r.stderr


# ─── update-intergraph-hyperedge (P10-C replace-only) ──────────────────────


class TestUpdateIntergraphHyperedgeCLI:
    def _seed(self, cli):
        cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--member-graph", "letter", "--member-node", "t",
            "--type", "COMPOSED_OF",
            "--intergraph-hyperedge-id", "ih1",
            "--json",
        )

    def test_replace_anchors_keeps_members(self, cli, hyperedge_metagraph):
        self._seed(cli)
        r = cli(
            "metagraph", "update-intergraph-hyperedge",
            "--name", "mg",
            "--intergraph-hyperedge-id", "ih1",
            "--anchor-graph", "word", "--anchor-node", "dog",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["anchors"] == [["word", "dog"]]
        assert len(out["members"]) == 3
        # P29 — edge_id stable across update.
        assert out["intergraph_hyperedge_id"] == "ih1"
        assert out["replaced_anchors"] is True
        assert out["replaced_members"] is False

    def test_replace_members_keeps_anchors(self, cli, hyperedge_metagraph):
        self._seed(cli)
        r = cli(
            "metagraph", "update-intergraph-hyperedge",
            "--name", "mg",
            "--intergraph-hyperedge-id", "ih1",
            "--member-graph", "letter", "--member-node", "d",
            "--member-graph", "letter", "--member-node", "o",
            "--member-graph", "letter", "--member-node", "g",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["anchors"] == [["word", "cat"]]
        assert out["members"] == [
            ["letter", "d"], ["letter", "o"], ["letter", "g"],
        ]

    def test_p19a_collapse_to_1_1_refused(self, cli, hyperedge_metagraph):
        self._seed(cli)
        r = cli(
            "metagraph", "update-intergraph-hyperedge",
            "--name", "mg",
            "--intergraph-hyperedge-id", "ih1",
            "--member-graph", "letter", "--member-node", "c",
            "--json",
        )
        assert r.returncode == 1
        assert "P19-A" in r.stderr

    def test_replace_properties_flag(self, cli, hyperedge_metagraph):
        cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--type", "T",
            "--prop", "a=1",
            "--intergraph-hyperedge-id", "ih1",
        )
        r = cli(
            "metagraph", "update-intergraph-hyperedge",
            "--name", "mg",
            "--intergraph-hyperedge-id", "ih1",
            "--prop", "b=2",
            "--replace-properties",
            "--json",
        )
        assert r.returncode == 0
        assert json.loads(r.stdout)["properties"] == {"b": 2}

    def test_compositional_update_refused(self, cli, hyperedge_metagraph):
        cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--type", "COMPOSED_OF",
            "--compositional",
            "--intergraph-hyperedge-id", "comp1",
        )
        r = cli(
            "metagraph", "update-intergraph-hyperedge",
            "--name", "mg",
            "--intergraph-hyperedge-id", "comp1",
            "--prop", "k=v",
            "--json",
        )
        assert r.returncode == 1
        assert "Compositional" in r.stderr


# ─── list-intergraph-hyperedges ────────────────────────────────────────────


class TestListIntergraphHyperedgesCLI:
    def test_empty(self, cli, hyperedge_metagraph):
        r = cli("metagraph", "list-intergraph-hyperedges", "--name", "mg", "--json")
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["intergraph_hyperedges"] == []
        assert out["metagraph"] == "mg"

    def test_after_add(self, cli, hyperedge_metagraph):
        cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--type", "T",
        )
        r = cli("metagraph", "list-intergraph-hyperedges", "--name", "mg", "--json")
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert len(out["intergraph_hyperedges"]) == 1
        ihe = out["intergraph_hyperedges"][0]
        assert ihe["anchors"] == [["word", "cat"]]
        assert ihe["type_name"] == "T"


# ─── 5-way set-prop mutex (extends 05b 4-way) ──────────────────────────────


class TestSetPropFiveWayMutex:
    def test_five_way_mutex_violation_two_flags(self, cli, hyperedge_metagraph):
        r = cli(
            "metagraph", "set-prop",
            "--name", "mg",
            "--on-metagraph",
            "--intergraph-hyperedge-id", "ih1",
            "--prop", "k=v",
        )
        assert r.returncode == 2
        assert "5-way" in r.stderr or "exactly one" in r.stderr.lower()

    def test_five_way_intergraph_hyperedge_path(self, cli, hyperedge_metagraph):
        cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--type", "T",
            "--intergraph-hyperedge-id", "ih1",
        )
        r = cli(
            "metagraph", "set-prop",
            "--name", "mg",
            "--intergraph-hyperedge-id", "ih1",
            "--prop", "weight=0.5",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["kind"] == "intergraph_hyperedge"
        assert out["properties"] == {"weight": 0.5}

    def test_set_prop_compositional_refused(self, cli, hyperedge_metagraph):
        cli(
            "metagraph", "add-intergraph-hyperedge",
            "--name", "mg",
            "--anchor-graph", "word", "--anchor-node", "cat",
            "--member-graph", "letter", "--member-node", "c",
            "--member-graph", "letter", "--member-node", "a",
            "--type", "COMPOSED_OF",
            "--compositional",
            "--intergraph-hyperedge-id", "comp1",
        )
        r = cli(
            "metagraph", "set-prop",
            "--name", "mg",
            "--intergraph-hyperedge-id", "comp1",
            "--prop", "k=v",
        )
        assert r.returncode == 1
        assert "Compositional" in r.stderr


# ─── add-intergraph-hyperedge-type (P12-A schema-mutation footgun) ─────────


class TestAddIntergraphHyperedgeTypeCLI:
    def _build_schema(self, cli):
        cli("metagraph-schema", "create", "--name", "ms")

    def test_happy_path_default_ordered_true(self, cli, _isolated_state_dir):
        self._build_schema(cli)
        r = cli(
            "metagraph-schema", "add-intergraph-hyperedge-type",
            "--schema", "ms",
            "--type-name", "COMPOSED_OF",
            "--allowed-anchor-type", "Word",
            "--allowed-member-type", "Letter",
            "--allowed-anchor-graph", "word",
            "--allowed-member-graph", "letter",
            "--prop-type", "weight=float",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        # P18-A — default ordered=True.
        assert out["ordered"] is True
        assert out["type_name"] == "COMPOSED_OF"
        assert sorted(out["allowed_anchor_types"]) == ["Word"]
        assert sorted(out["allowed_member_graphs"]) == ["letter"]

    def test_unordered_flag(self, cli, _isolated_state_dir):
        self._build_schema(cli)
        r = cli(
            "metagraph-schema", "add-intergraph-hyperedge-type",
            "--schema", "ms",
            "--type-name", "UNORDERED_T",
            "--unordered",
            "--json",
        )
        assert r.returncode == 0
        assert json.loads(r.stdout)["ordered"] is False

    def test_invalid_cypher_name_refused(self, cli, _isolated_state_dir):
        self._build_schema(cli)
        r = cli(
            "metagraph-schema", "add-intergraph-hyperedge-type",
            "--schema", "ms",
            "--type-name", "lowercase",
            "--json",
        )
        assert r.returncode == 1
        assert "Cypher" in r.stderr

    def test_p12a_warning_when_attached(self, cli, hyperedge_metagraph):
        # Build a schema, attach to mg, then add-type should warn.
        cli("metagraph-schema", "create", "--name", "ms")
        cli(
            "metagraph", "attach-schema",
            "--name", "mg", "--schema", "ms", "--json",
        )
        r = cli(
            "metagraph-schema", "add-intergraph-hyperedge-type",
            "--schema", "ms",
            "--type-name", "FOO",
            "--json",
        )
        assert r.returncode == 0
        # P12-A — stderr warning lists attached metagraphs.
        assert "P12-A" in r.stderr or "warning" in r.stderr.lower()
        assert "mg" in r.stderr


# ─── inspect/list shape additive extensions ────────────────────────────────


class TestInspectListShapeExtensions:
    def test_metagraph_inspect_includes_intergraph_hyperedges_count(
        self, cli, hyperedge_metagraph
    ):
        r = cli("metagraph", "inspect", "--name", "mg", "--json")
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert "intergraph_hyperedges" in out["counts"]
        assert out["counts"]["intergraph_hyperedges"] == 0

    def test_metagraph_list_includes_intergraph_hyperedges_count(
        self, cli, hyperedge_metagraph
    ):
        r = cli("metagraph", "list", "--json")
        assert r.returncode == 0
        out = json.loads(r.stdout)
        for entry in out["metagraphs"]:
            assert "intergraph_hyperedges_count" in entry

    def test_metagraph_schema_inspect_includes_hyperedge_types(
        self, cli, _isolated_state_dir
    ):
        cli("metagraph-schema", "create", "--name", "ms")
        r = cli("metagraph-schema", "inspect", "--name", "ms", "--json")
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert "intergraph_hyperedge_types" in out
        assert "intergraph_hyperedge_types" in out["counts"]


# ─── P31 — P13-B workaround regression coverage ────────────────────────────


class TestP13BWorkaround:
    """P31 (this chat B) — verify the documented workaround for the
    deferred ``update_intergraph_edge_endpoints`` (P13-B retreat) still
    works under 05c. Workaround: ``remove-intergraph-edge`` + ``add-intergraph-edge
    --intergraph-edge-id <orig>`` preserves edge_id stability."""

    def test_workaround_preserves_edge_id_on_non_compositional(
        self, cli, _isolated_state_dir
    ):
        # Build minimal binary fixture.
        cli("graph", "create", "--name", "lex", "--role", "lexicon")
        cli(
            "graph", "add-node", "cat",
            "--name", "lex", "--node-id", "n_cat", "--type", "Word",
        )
        cli("graph", "create", "--name", "cpt", "--role", "concepts")
        cli(
            "graph", "add-node", "Cat#1",
            "--name", "cpt", "--node-id", "n_concept", "--type", "Concept",
        )
        cli(
            "graph", "add-node", "Cat#2",
            "--name", "cpt", "--node-id", "n_concept2", "--type", "Concept",
        )
        cli("metagraph", "create", "--name", "mg")
        cli("metagraph", "add-graph", "--name", "mg", "--graph", "lex")
        cli("metagraph", "add-graph", "--name", "mg", "--graph", "cpt")
        # Add edge with explicit id.
        r = cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept",
            "--type", "EVOKES",
            "--intergraph-edge-id", "preserve-me",
            "--json",
        )
        assert r.returncode == 0
        # Workaround step 1: remove.
        r = cli(
            "metagraph", "remove-intergraph-edge",
            "--name", "mg",
            "--intergraph-edge-id", "preserve-me",
            "--json",
        )
        assert r.returncode == 0
        # Workaround step 2: re-add with same id, different target.
        r = cli(
            "metagraph", "add-intergraph-edge",
            "--name", "mg",
            "--source-graph", "lex", "--source-node", "n_cat",
            "--target-graph", "cpt", "--target-node", "n_concept2",
            "--type", "EVOKES",
            "--intergraph-edge-id", "preserve-me",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        # Edge id preserved across the workaround.
        assert out["edge_id"] == "preserve-me"
        # Target re-pointed.
        assert out["target_node"] == "n_concept2"
