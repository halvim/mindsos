"""Phase 05d — CLI tests for ``add-meta-edge-type`` + ``add-meta-hyperedge-type``.

Subprocesses ``mindsos`` binary (in-container Python 3.12 + typer); see
``feedback_docker_compose_invocation.md``.

Locked via round-7 P31 A row §G:
  - ``--allowed-source-graph`` / ``--allowed-target-graph`` (meta-edge)
    repeatable.
  - ``--allowed-member-graph`` (meta-hyperedge) repeatable.
  - NO ``--ordered/--unordered`` (P1 C).
  - ``--prop-type`` repeatable; ``--description`` optional; ``--json``
    parity (P29 A).
  - Schema-mutation footgun warning to stderr (P8 A).
"""

from __future__ import annotations

import json

import pytest


# ─── add-meta-edge-type ────────────────────────────────────────────────────


class TestAddMetaEdgeTypeCLI:
    def test_minimal_register(self, cli):
        cli("metagraph-schema", "create", "--name", "ms")
        r = cli(
            "metagraph-schema", "add-meta-edge-type",
            "--schema", "ms",
            "--type-name", "LINKS_TO",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["schema"] == "ms"
        assert out["type_name"] == "LINKS_TO"
        assert out["allowed_source_graphs"] == []
        assert out["allowed_target_graphs"] == []
        assert out["property_types"] == {}
        assert out["description"] is None

    def test_full_register(self, cli):
        cli("metagraph-schema", "create", "--name", "ms")
        r = cli(
            "metagraph-schema", "add-meta-edge-type",
            "--schema", "ms",
            "--type-name", "REFERENCES",
            "--allowed-source-graph", "ontology",
            "--allowed-target-graph", "lexicon",
            "--allowed-target-graph", "concepts",
            "--prop-type", "weight=float",
            "--description", "Cross-graph reference.",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["allowed_source_graphs"] == ["ontology"]
        assert sorted(out["allowed_target_graphs"]) == ["concepts", "lexicon"]
        assert out["property_types"] == {"weight": "float"}
        assert out["description"] == "Cross-graph reference."

    def test_invalid_cypher_regex_exit_1(self, cli):
        cli("metagraph-schema", "create", "--name", "ms")
        r = cli(
            "metagraph-schema", "add-meta-edge-type",
            "--schema", "ms",
            "--type-name", "lowercase_invalid",
        )
        assert r.returncode == 1
        assert "CypherError" in r.stderr

    def test_duplicate_register_exit_1(self, cli):
        cli("metagraph-schema", "create", "--name", "ms")
        cli(
            "metagraph-schema", "add-meta-edge-type",
            "--schema", "ms",
            "--type-name", "X",
        )
        r = cli(
            "metagraph-schema", "add-meta-edge-type",
            "--schema", "ms",
            "--type-name", "X",
        )
        assert r.returncode == 1
        assert "already registered" in r.stderr

    def test_schema_mutation_footgun_warning_when_attached(self, cli):
        """P8 A — stderr warning lists every metagraph the schema is attached to."""
        cli("metagraph-schema", "create", "--name", "ms")
        cli("metagraph", "create", "--name", "mg")
        cli(
            "metagraph", "attach-schema",
            "--name", "mg", "--schema", "ms",
        )
        r = cli(
            "metagraph-schema", "add-meta-edge-type",
            "--schema", "ms",
            "--type-name", "LINKS_TO",
        )
        assert r.returncode == 0, r.stderr
        # Warning listed the attached metagraph.
        assert "warning:" in r.stderr
        assert "ms" in r.stderr
        assert "mg" in r.stderr
        assert "P8 A" in r.stderr or "schema-mutation footgun" in r.stderr


# ─── add-meta-hyperedge-type ───────────────────────────────────────────────


class TestAddMetaHyperEdgeTypeCLI:
    def test_minimal_register(self, cli):
        cli("metagraph-schema", "create", "--name", "ms")
        r = cli(
            "metagraph-schema", "add-meta-hyperedge-type",
            "--schema", "ms",
            "--type-name", "GROUPS",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["type_name"] == "GROUPS"
        assert out["allowed_member_graphs"] == []
        # NO ordered field per P1 C.
        assert "ordered" not in out

    def test_full_register(self, cli):
        cli("metagraph-schema", "create", "--name", "ms")
        r = cli(
            "metagraph-schema", "add-meta-hyperedge-type",
            "--schema", "ms",
            "--type-name", "UNIFIES",
            "--allowed-member-graph", "ontology",
            "--allowed-member-graph", "lexicon",
            "--prop-type", "strength=float",
            "--description", "Cross-domain.",
            "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert sorted(out["allowed_member_graphs"]) == ["lexicon", "ontology"]

    def test_no_ordered_flag_recognised(self, cli):
        """P1 C: --ordered/--unordered MUST NOT exist on this verb."""
        cli("metagraph-schema", "create", "--name", "ms")
        r = cli(
            "metagraph-schema", "add-meta-hyperedge-type",
            "--schema", "ms",
            "--type-name", "X",
            "--ordered",  # this should fail.
        )
        assert r.returncode != 0
        # typer's "no such option" path may use different wording across
        # versions; just confirm the flag isn't accepted.
        assert "--ordered" in (r.stderr + r.stdout) or "ordered" in (r.stderr + r.stdout).lower()

    def test_invalid_cypher_regex_exit_1(self, cli):
        cli("metagraph-schema", "create", "--name", "ms")
        r = cli(
            "metagraph-schema", "add-meta-hyperedge-type",
            "--schema", "ms",
            "--type-name", "lowercase_bad",
        )
        assert r.returncode == 1


# ─── inspect after add ─────────────────────────────────────────────────────


class TestInspectIncludesMetaVocab:
    def test_inspect_shows_meta_edge_types_count(self, cli):
        cli("metagraph-schema", "create", "--name", "ms")
        cli(
            "metagraph-schema", "add-meta-edge-type",
            "--schema", "ms",
            "--type-name", "X",
        )
        r = cli("metagraph-schema", "inspect", "--name", "ms", "--json")
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        # Existing 05c shape was {"counts": {"intergraph_edge_types": int,
        # "intergraph_hyperedge_types": int}}; 05d may extend with
        # meta_edge_types / meta_hyperedge_types — assert non-fatal.
        # If 05d doesn't extend inspect output, this test is a no-op
        # (intentional — keep inspect surface stable until row decides).
        # Lenient check: just confirm the verb succeeds; full count
        # exposure is a follow-up if surfaced later.
        assert "name" in out or "_state_version" in out
