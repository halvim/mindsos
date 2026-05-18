"""Phase 13 PB-6 — ``mindsos knowledge schema {show,validate}`` CLI.

Two representative roles (lexicon = seed; memories = upper-layer)
exercise the verbs end-to-end. Each verb covers happy / JSON / error.

State-file fixtures use canonical ``node_id`` / ``edge_id`` keys per
`feedback_state_file_key_canonicalization.md` (B-11-T2 lock).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


_FIXTURES = Path(__file__).parent / "fixtures"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "mindsos_cli", *args],
        capture_output=True,
        text=True,
    )


# ── schema show ────────────────────────────────────────────────────────


def test_schema_show_lexicon_happy() -> None:
    res = _run(["knowledge", "schema", "show", "--role", "lexicon"])
    assert res.returncode == 0, res.stderr
    assert "node_types" in res.stdout
    assert "Lemma" in res.stdout
    assert "HAS_SENSE" in res.stdout


def test_schema_show_lexicon_json() -> None:
    res = _run(["knowledge", "schema", "show", "--role", "lexicon", "--json"])
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["role"] == "lexicon"
    assert payload["strict"] is False
    assert "Lemma" in payload["node_types"]
    assert "HAS_SENSE" in payload["edge_types"]


def test_schema_show_memories_json() -> None:
    res = _run(["knowledge", "schema", "show", "--role", "memories", "--json"])
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["role"] == "memories"
    assert "Memory" in payload["node_types"]


def test_schema_show_alignment_prefix() -> None:
    res = _run(
        [
            "knowledge",
            "schema",
            "show",
            "--role",
            "alignment:lexicon<->concepts",
            "--json",
        ]
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["role"] == "alignment:lexicon<->concepts"
    assert "AlignmentAnchor" in payload["node_types"]
    assert "EXACT_MATCH" in payload["edge_types"]


def test_schema_show_unknown_role_exits_one() -> None:
    res = _run(["knowledge", "schema", "show", "--role", "not-a-real-role"])
    assert res.returncode == 1
    assert "UnknownRoleError" in res.stderr


# ── schema validate ────────────────────────────────────────────────────


def test_schema_validate_lexicon_happy_fixture() -> None:
    res = _run(
        [
            "knowledge",
            "schema",
            "validate",
            "--role",
            "lexicon",
            "--graph-file",
            str(_FIXTURES / "lexicon_happy.json"),
        ]
    )
    assert res.returncode == 0, res.stderr
    assert "OK" in res.stdout


def test_schema_validate_lexicon_happy_json() -> None:
    res = _run(
        [
            "knowledge",
            "schema",
            "validate",
            "--role",
            "lexicon",
            "--graph-file",
            str(_FIXTURES / "lexicon_happy.json"),
            "--json",
        ]
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["ok"] is True
    assert payload["violation_count"] == 0


def test_schema_validate_memories_bad_fixture_exits_one() -> None:
    res = _run(
        [
            "knowledge",
            "schema",
            "validate",
            "--role",
            "memories",
            "--graph-file",
            str(_FIXTURES / "memories_bad.json"),
        ]
    )
    assert res.returncode == 1
    assert "VIOLATIONS" in res.stdout


def test_schema_validate_memories_bad_fixture_json() -> None:
    res = _run(
        [
            "knowledge",
            "schema",
            "validate",
            "--role",
            "memories",
            "--graph-file",
            str(_FIXTURES / "memories_bad.json"),
            "--json",
        ]
    )
    assert res.returncode == 1
    payload = json.loads(res.stdout)
    assert payload["ok"] is False
    assert payload["violation_count"] >= 1


def test_schema_validate_exit_zero_surfaces_violation_but_returns_zero() -> None:
    res = _run(
        [
            "knowledge",
            "schema",
            "validate",
            "--role",
            "memories",
            "--graph-file",
            str(_FIXTURES / "memories_bad.json"),
            "--json",
            "--exit-zero",
        ]
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["ok"] is False
    assert payload["violation_count"] >= 1


def test_schema_validate_missing_graph_file_exits_one() -> None:
    res = _run(
        [
            "knowledge",
            "schema",
            "validate",
            "--role",
            "lexicon",
            "--graph-file",
            "/no/such/path-phase-13-test.json",
        ]
    )
    assert res.returncode == 1
    assert "not found" in res.stderr.lower()


def test_schema_validate_unknown_role_exits_one() -> None:
    res = _run(
        [
            "knowledge",
            "schema",
            "validate",
            "--role",
            "not-a-real-role",
            "--graph-file",
            str(_FIXTURES / "lexicon_happy.json"),
        ]
    )
    assert res.returncode == 1
    assert "UnknownRoleError" in res.stderr


def test_schema_help_lists_show_and_validate() -> None:
    res = _run(["knowledge", "schema", "--help"])
    assert res.returncode == 0
    assert "show" in res.stdout
    assert "validate" in res.stdout
