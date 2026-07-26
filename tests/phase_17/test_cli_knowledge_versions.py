"""Phase 17 retirement — `mindsos knowledge versions` CLI verb tests.

The verb reads a metagraph state-file by ``--metagraph NAME`` (Phase
03+ convention; mirrors Phase 16 ``admin promote {list, similarity}``
sourcing pattern). Per ADR-0150 §amendment-3, version is IRI-string
only — output reflects what `parse_iri(node_id).version` returns.

Phase 14 PB-13 partial closure: `versions` ships; `active-version`
verb was dropped per PB-15 vacuum (covered by retirement sentinels).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindsos_cli.app import app
from tests.phase_17.fixtures.build_versioning_corpus import (
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
    def test_versions_verb_in_knowledge_help(self) -> None:
        result = runner.invoke(app, ["knowledge", "--help"])
        assert result.exit_code == 0
        assert "versions" in result.stdout

    def test_versions_help_lists_flags(self) -> None:
        result = runner.invoke(app, ["knowledge", "versions", "--help"])
        assert result.exit_code == 0
        assert "--metagraph" in result.stdout
        assert "--role" in result.stdout
        assert "--json" in result.stdout

    def test_active_version_verb_not_registered(self) -> None:
        """Phase 14 PB-13 second-half: `active-version` dropped per PB-15 vacuum."""
        result = runner.invoke(
            app, ["knowledge", "active-version", "--help"]
        )
        # Typer returns exit_code != 0 for unknown subcommand.
        assert result.exit_code != 0


# ── §2 All-roles enumeration (no --role) ───────────────────────────────


class TestAllRolesEnumeration:
    def test_text_output_lists_all_roles(self, state_dir: Path) -> None:
        result = runner.invoke(
            app, ["knowledge", "versions", "--metagraph", CORPUS_NAME]
        )
        assert result.exit_code == 0, result.stdout
        # All 6 named roles surface in some form.
        for role in (
            "ontology",
            "lexicon",
            "concepts",
            "promoted-pipelines",
            "request-patterns",
            "problem-trace",
        ):
            assert role in result.stdout

    def test_text_output_shows_ontology_two_versions(
        self, state_dir: Path
    ) -> None:
        result = runner.invoke(
            app, ["knowledge", "versions", "--metagraph", CORPUS_NAME]
        )
        assert result.exit_code == 0
        # Per ADR-0150 §amendment-3: 4.1 + 4.2 coexist in one role-graph.
        assert "4.1" in result.stdout
        assert "4.2" in result.stdout

    def test_empty_role_graph_reports_no_versions(
        self, state_dir: Path
    ) -> None:
        result = runner.invoke(
            app, ["knowledge", "versions", "--metagraph", CORPUS_NAME]
        )
        assert result.exit_code == 0
        # `promoted-pipelines` is empty in the corpus.
        assert "no version-qualified IRIs" in result.stdout

    def test_json_output_is_role_to_sorted_version_list(
        self, state_dir: Path
    ) -> None:
        result = runner.invoke(
            app,
            [
                "knowledge",
                "versions",
                "--metagraph",
                CORPUS_NAME,
                "--json",
            ],
        )
        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        assert payload["ontology"] == ["4.1", "4.2"]
        assert payload["lexicon"] == ["2024"]
        assert payload["concepts"] == ["1.7"]
        assert payload["promoted-pipelines"] == []


# ── §3 Single-role filter (--role) ─────────────────────────────────────


class TestRoleFilter:
    def test_text_filter_to_single_role(self, state_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "knowledge",
                "versions",
                "--metagraph",
                CORPUS_NAME,
                "--role",
                "ontology",
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert "ontology" in result.stdout
        # Other roles do NOT surface in the output.
        assert "lexicon" not in result.stdout
        assert "concepts" not in result.stdout

    def test_json_filter_to_single_role(self, state_dir: Path) -> None:
        result = runner.invoke(
            app,
            [
                "knowledge",
                "versions",
                "--metagraph",
                CORPUS_NAME,
                "--role",
                "ontology",
                "--json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert list(payload.keys()) == ["ontology"]
        assert payload["ontology"] == ["4.1", "4.2"]
