"""Phase 16 — `mindsos admin promote {list, similarity}` CLI verb tests.

Per Phase 16 PB-I1: CLI sources a metagraph state-file by NAME
(``--metagraph NAME`` — Phase 03+ convention; reader is the Phase 09
state-file reader via :func:`mindsos_cli.commands.metagraph._load_or_die`).

Both verbs are read-only; both support ``--json``. The Phase 24
``promote propose`` verb is NOT registered at Phase 16 (per PB-1c
reframe).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindsos_cli.app import app
from tests.phase_16.fixtures.build_corpus import (
    CORPUS_NAME,
    save_corpus_to_state_dir,
)


runner = CliRunner()


@pytest.fixture
def state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(tmp_path))
    save_corpus_to_state_dir(tmp_path)
    return tmp_path


# ── §1 Help surfaces ───────────────────────────────────────────────────


class TestHelpSurface:
    def test_promote_group_in_admin_help(self) -> None:
        result = runner.invoke(app, ["admin", "--help"])
        assert result.exit_code == 0
        assert "promote" in result.stdout

    def test_promote_group_lists_two_verbs(self) -> None:
        result = runner.invoke(app, ["admin", "promote", "--help"])
        assert result.exit_code == 0
        assert "list" in result.stdout
        assert "similarity" in result.stdout

    def test_promote_propose_is_not_registered(self) -> None:
        # PB-1c — propose verb defers to Phase 24.
        result = runner.invoke(app, ["admin", "promote", "propose", "--help"])
        # Typer returns exit_code != 0 for unknown subcommand.
        assert result.exit_code != 0

    def test_promote_list_help_lists_flags(self) -> None:
        result = runner.invoke(app, ["admin", "promote", "list", "--help"])
        assert result.exit_code == 0
        assert "--metagraph" in result.stdout
        assert "--role" in result.stdout
        assert "--node-type" in result.stdout
        assert "--json" in result.stdout

    def test_promote_similarity_help_lists_flags(self) -> None:
        result = runner.invoke(
            app, ["admin", "promote", "similarity", "--help"]
        )
        assert result.exit_code == 0
        assert "--metagraph" in result.stdout
        assert "--role" in result.stdout
        assert "--threshold-blocking" in result.stdout
        assert "--threshold-review" in result.stdout
        assert "--json" in result.stdout


# ── §2 promote list ────────────────────────────────────────────────────


class TestPromoteList:
    def test_list_text_output(self, state_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "admin", "promote", "list",
                "--metagraph", CORPUS_NAME,
                "--role", "ontology",
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert "candidates=" in result.stdout
        assert "Class" in result.stdout

    def test_list_json_output(self, state_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "admin", "promote", "list",
                "--metagraph", CORPUS_NAME,
                "--role", "ontology",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        assert isinstance(payload, list)
        for c in payload:
            assert c["role"] == "ontology"
            assert c["node_type"] == "Class"
            assert c["source_user_id"] is None

    def test_list_node_type_filter(self, state_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "admin", "promote", "list",
                "--metagraph", CORPUS_NAME,
                "--role", "lexicon",
                "--node-type", "Synset",
                "--json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert all(c["node_type"] == "Synset" for c in payload)


# ── §3 promote similarity ──────────────────────────────────────────────


class TestPromoteSimilarity:
    def test_similarity_text_output(self, state_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "admin", "promote", "similarity",
                "--metagraph", CORPUS_NAME,
                "--role", "ontology",
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert "report_id=" in result.stdout
        assert "threshold_blocking=0.85" in result.stdout
        assert "threshold_review=0.5" in result.stdout
        assert "findings=" in result.stdout

    def test_similarity_json_output(self, state_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "admin", "promote", "similarity",
                "--metagraph", CORPUS_NAME,
                "--role", "ontology",
                "--json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert "report_id" in payload
        assert "findings" in payload
        assert payload["threshold_blocking"] == 0.85
        assert payload["threshold_review"] == 0.5

    def test_similarity_custom_thresholds(self, state_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "admin", "promote", "similarity",
                "--metagraph", CORPUS_NAME,
                "--role", "ontology",
                "--threshold-blocking", "0.95",
                "--threshold-review", "0.25",
                "--json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["threshold_blocking"] == 0.95
        assert payload["threshold_review"] == 0.25
        # Custom thresholds change the report_id (per ADR-0052 §amendment-1).

    def test_similarity_unknown_metagraph_fails(
        self, state_dir: Path
    ) -> None:
        result = runner.invoke(
            app,
            [
                "admin", "promote", "similarity",
                "--metagraph", "does-not-exist",
                "--role", "ontology",
            ],
        )
        assert result.exit_code != 0
