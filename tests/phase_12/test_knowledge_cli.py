"""Tier 4 — `mindsos knowledge` CLI surface.

In-process tests via `typer.testing.CliRunner` to keep the test image
boot cheap; subprocess parity is covered by the cumulative Phase 02
pattern. All five verbs covered:

  knowledge iri build --role R [--kind K] [--<arg> ...] [--json]
  knowledge iri parse <iri> [--json]
  knowledge iri validate <iri> [--json]
  knowledge ref-types --list [--json]
  knowledge roles --list [--seed-only|--upper-only] [--json]
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


# ── iri build ──────────────────────────────────────────────────────────


def test_iri_build_dolce_happy() -> None:
    result = runner.invoke(
        app,
        [
            "knowledge", "iri", "build",
            "--role", "ontology",
            "--version", "4.0",
            "--fragment", "PhysicalObject",
        ],
    )
    assert result.exit_code == 0
    assert "dolce-dul-4.0:PhysicalObject" in result.stdout


def test_iri_build_memory_happy_json() -> None:
    result = runner.invoke(
        app,
        [
            "knowledge", "iri", "build",
            "--role", "episodic_memories",
            "--kind", "memory",
            "--version", "1",
            "--user-id", "alice",
            "--memory-id", "m1",
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["iri"] == "episodic-memories-1:memory:alice:m1"
    assert payload["role"] == "episodic_memories"
    assert payload["kind"] == "memory"


def test_iri_build_unknown_role_exit_2() -> None:
    result = runner.invoke(
        app,
        ["knowledge", "iri", "build", "--role", "bogus", "--version", "1"],
    )
    assert result.exit_code == 2
    assert "Unknown role" in result.stderr or "Unknown role" in result.output


def test_iri_build_missing_kind_for_multi_kind_role_exit_2() -> None:
    result = runner.invoke(
        app,
        [
            "knowledge", "iri", "build",
            "--role", "episodic_memories",
            "--version", "1",
            "--user-id", "alice",
            "--memory-id", "m1",
        ],
    )
    assert result.exit_code == 2


def test_iri_build_bad_user_id_exit_1() -> None:
    result = runner.invoke(
        app,
        [
            "knowledge", "iri", "build",
            "--role", "episodic_memories",
            "--kind", "memory",
            "--version", "1",
            "--user-id", "bad:colon",
            "--memory-id", "m1",
        ],
    )
    assert result.exit_code == 1
    assert "RefFormatError" in (result.stderr or result.output)


# ── iri parse ──────────────────────────────────────────────────────────


def test_iri_parse_happy() -> None:
    result = runner.invoke(
        app,
        ["knowledge", "iri", "parse", "oewn-2024:synset:01234567-n", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["role"] == "lexicon"
    assert payload["kind"] == "synset"
    assert payload["body"] == "01234567-n"


def test_iri_parse_bad_input_exit_1() -> None:
    result = runner.invoke(
        app,
        ["knowledge", "iri", "parse", "not-an-iri"],
    )
    assert result.exit_code == 1


def test_iri_parse_human_output_shape() -> None:
    result = runner.invoke(
        app,
        ["knowledge", "iri", "parse", "dolce-dul-4.0:PhysicalObject"],
    )
    assert result.exit_code == 0
    assert "role" in result.stdout
    assert "ontology" in result.stdout


# ── iri validate ───────────────────────────────────────────────────────


def test_iri_validate_valid() -> None:
    result = runner.invoke(
        app,
        ["knowledge", "iri", "validate", "dolce-dul-4.0:PhysicalObject"],
    )
    assert result.exit_code == 0


def test_iri_validate_invalid() -> None:
    result = runner.invoke(
        app,
        ["knowledge", "iri", "validate", "not-an-iri"],
    )
    assert result.exit_code == 1


def test_iri_validate_alignment_role_is_invalid() -> None:
    # PB-4: alignment_role output is NOT a version-qualified IRI.
    result = runner.invoke(
        app,
        ["knowledge", "iri", "validate", "alignment:concepts:lexicon"],
    )
    assert result.exit_code == 1


# ── ref-types --list ───────────────────────────────────────────────────


def test_ref_types_list_json() -> None:
    result = runner.invoke(app, ["knowledge", "ref-types", "--list", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "PROMOTED" in payload["ref_types"]
    assert len(payload["ref_types"]) == 7


def test_ref_types_missing_list_flag_exit_2() -> None:
    result = runner.invoke(app, ["knowledge", "ref-types"])
    assert result.exit_code == 2


def test_ref_types_list_human() -> None:
    result = runner.invoke(app, ["knowledge", "ref-types", "--list"])
    assert result.exit_code == 0
    assert "SPECIALISES" in result.stdout
    assert "PROMOTED" in result.stdout


# ── roles --list ───────────────────────────────────────────────────────


def test_roles_list_all_json() -> None:
    result = runner.invoke(app, ["knowledge", "roles", "--list", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    names = {r["name"] for r in payload["roles"]}
    assert names == {
        "ontology", "lexicon", "concepts",
        "promoted-pipelines", "task-patterns", "episodic_memories",
        "problem-trace", "capacity-state",
        # Phase 43 (ADR-0150 §am-5) additions.
        "parameter-staging", "pending-promotions",
        "capacity-gaps", "learned-parameters",
    }


def test_roles_list_seed_only() -> None:
    result = runner.invoke(
        app, ["knowledge", "roles", "--list", "--seed-only", "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    names = {r["name"] for r in payload["roles"]}
    assert names == {"ontology", "lexicon", "concepts"}


def test_roles_list_upper_only() -> None:
    result = runner.invoke(
        app, ["knowledge", "roles", "--list", "--upper-only", "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    names = {r["name"] for r in payload["roles"]}
    assert names == {
        "promoted-pipelines", "task-patterns", "episodic_memories",
        "problem-trace", "capacity-state",
        # Phase 43 (ADR-0150 §am-5) upper-layer additions.
        "parameter-staging", "pending-promotions",
        "capacity-gaps", "learned-parameters",
    }


def test_roles_list_mutex_exit_2() -> None:
    result = runner.invoke(
        app,
        ["knowledge", "roles", "--list", "--seed-only", "--upper-only"],
    )
    assert result.exit_code == 2
