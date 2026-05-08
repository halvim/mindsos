"""Phase 05d — CLI tests for ``mindsos metagraph-schema validate``.

Locks per round-7 P9 B + P32 A + P40 A + P41 A:
  - Default: ``validate --metagraph MG`` resolves schema via
    ``MG.schema_name``.
  - ``--schema MS`` opt-in (P32 A): validates against explicit schema
    without touching ``MG.schema_name``.
  - Exit codes (P41 A): 0 pass / 1 violation / 2 resource-not-found /
    3 no-usable-schema.
  - ``--json`` shape (P40 A): {passed, schema_name, metagraph_name,
    violations} — NO ``vocab_fingerprint_match`` field.
"""

from __future__ import annotations

import json

import pytest


class TestValidatePassPath:
    def test_attached_passes(self, cli):
        cli("metagraph-schema", "create", "--name", "ms")
        cli("metagraph", "create", "--name", "mg")
        cli("metagraph", "attach-schema", "--name", "mg", "--schema", "ms")
        r = cli("metagraph-schema", "validate", "--metagraph", "mg")
        assert r.returncode == 0, r.stderr
        assert "ok" in r.stdout

    def test_json_shape_on_pass(self, cli):
        cli("metagraph-schema", "create", "--name", "ms")
        cli("metagraph", "create", "--name", "mg")
        cli("metagraph", "attach-schema", "--name", "mg", "--schema", "ms")
        r = cli(
            "metagraph-schema", "validate",
            "--metagraph", "mg", "--json",
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        # P40 A — no vocab_fingerprint_match field.
        assert set(out.keys()) == {
            "passed", "schema_name", "metagraph_name", "violations",
        }
        assert out["passed"] is True
        assert out["schema_name"] == "ms"
        assert out["metagraph_name"] == "mg"
        assert out["violations"] == []


class TestValidateNoUsableSchema:
    """P41 A — exit code 3 for ``no usable schema``."""

    def test_no_attached_no_explicit_exits_3(self, cli):
        cli("metagraph", "create", "--name", "mg")
        r = cli("metagraph-schema", "validate", "--metagraph", "mg")
        assert r.returncode == 3, r.stderr
        assert "no schema" in r.stderr or "no usable schema" in r.stderr

    def test_no_attached_no_explicit_json_shape(self, cli):
        cli("metagraph", "create", "--name", "mg")
        r = cli(
            "metagraph-schema", "validate",
            "--metagraph", "mg", "--json",
        )
        assert r.returncode == 3
        out = json.loads(r.stdout)
        assert out["passed"] is False
        assert out["schema_name"] is None


class TestValidateResourceNotFound:
    """P41 A — exit code 2 for missing schema or metagraph."""

    def test_missing_metagraph_exits_2(self, cli):
        r = cli(
            "metagraph-schema", "validate",
            "--metagraph", "doesnotexist",
        )
        assert r.returncode == 2, r.stderr

    def test_missing_explicit_schema_exits_2(self, cli):
        cli("metagraph", "create", "--name", "mg")
        r = cli(
            "metagraph-schema", "validate",
            "--metagraph", "mg",
            "--schema", "doesnotexist",
        )
        assert r.returncode == 2, r.stderr


class TestValidateExplicitSchemaOptIn:
    """P32 A — ``--schema MS`` opt-in path validates against explicit
    schema without mutating ``MG.schema_name``.
    """

    def test_explicit_schema_passes(self, cli):
        # Build a schema separately; never attach.
        cli("metagraph-schema", "create", "--name", "ms_test")
        cli("metagraph", "create", "--name", "mg")
        r = cli(
            "metagraph-schema", "validate",
            "--metagraph", "mg",
            "--schema", "ms_test",
        )
        # Empty MG + empty schema = pass.
        assert r.returncode == 0, r.stderr

    def test_explicit_schema_does_not_mutate_attachment(self, cli):
        cli("metagraph-schema", "create", "--name", "ms_test")
        cli("metagraph", "create", "--name", "mg")
        cli(
            "metagraph-schema", "validate",
            "--metagraph", "mg",
            "--schema", "ms_test",
        )
        # The metagraph must still have NO schema attached.
        r = cli("metagraph", "inspect", "--name", "mg", "--json")
        out = json.loads(r.stdout)
        assert out["schema_name"] is None


class TestValidateViolationPath:
    """P41 A — exit code 1 for at least one violation."""

    def test_metaedge_with_unknown_type_fails(self, cli):
        # Build a metagraph with a metaedge.
        cli("graph", "create", "--name", "ont", "--role", "ontology")
        cli("graph", "create", "--name", "lex", "--role", "lexicon")
        cli("metagraph", "create", "--name", "mg")
        cli("metagraph", "add-graph", "--name", "mg", "--graph", "ont")
        cli("metagraph", "add-graph", "--name", "mg", "--graph", "lex")
        cli(
            "metagraph", "add-metaedge",
            "--name", "mg",
            "--source-graph", "ont", "--target-graph", "lex",
            "--type", "LINKS_TO",
        )
        # Build a schema with a non-matching meta_edge_type vocab.
        cli("metagraph-schema", "create", "--name", "ms")
        cli(
            "metagraph-schema", "add-meta-edge-type",
            "--schema", "ms",
            "--type-name", "OTHER_TYPE",
        )
        # Validate using --schema opt-in (without attaching, since attach
        # would refuse with the same vocab gap).
        r = cli(
            "metagraph-schema", "validate",
            "--metagraph", "mg",
            "--schema", "ms",
            "--json",
        )
        assert r.returncode == 1, r.stderr
        out = json.loads(r.stdout)
        assert out["passed"] is False
        assert len(out["violations"]) == 1
        v = out["violations"][0]
        assert v["primitive"] == "MetaEdge"
        assert v["type_name"] == "LINKS_TO"
        assert v["rule"] == "type_or_role"


class TestValidateEmptyVocabPassSilently:
    """P39 A — empty MetaEdgeType vocab + non-strict + existing
    metaedges → passes silently in validate (mirrors eager-attach).
    """

    def test_empty_vocab_non_strict_passes(self, cli):
        cli("graph", "create", "--name", "ont", "--role", "ontology")
        cli("graph", "create", "--name", "lex", "--role", "lexicon")
        cli("metagraph", "create", "--name", "mg")
        cli("metagraph", "add-graph", "--name", "mg", "--graph", "ont")
        cli("metagraph", "add-graph", "--name", "mg", "--graph", "lex")
        cli(
            "metagraph", "add-metaedge",
            "--name", "mg",
            "--source-graph", "ont", "--target-graph", "lex",
            "--type", "LINKS_TO",
        )
        cli("metagraph-schema", "create", "--name", "ms")
        # No MetaEdgeType registered; non-strict default.
        cli("metagraph", "attach-schema", "--name", "mg", "--schema", "ms")
        r = cli("metagraph-schema", "validate", "--metagraph", "mg")
        # Empty vocab + non-strict → pass silently per P39 A.
        assert r.returncode == 0, r.stderr
