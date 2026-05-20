"""Phase 15a — `mindsos admin import` CLI verb tests.

Per Phase 15a PB-4a/PB-10: CLI namespace is `mindsos admin import
{dolce,oewn,framenet}`. Each verb is a dry-run that prints
ImportResult to stdout (text default; JSON on `--json`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindsos_cli.app import app


FIXTURE_DIR = Path(__file__).parent / "fixtures"
runner = CliRunner()


def test_admin_group_in_help() -> None:
    result = runner.invoke(app, ["admin", "--help"])
    assert result.exit_code == 0
    assert "import" in result.stdout


def test_admin_import_subgroup_lists_three_phase_15a_verbs() -> None:
    result = runner.invoke(app, ["admin", "import", "--help"])
    assert result.exit_code == 0
    for verb in ("dolce", "oewn", "framenet"):
        assert verb in result.stdout


def test_admin_import_dolce_help() -> None:
    result = runner.invoke(app, ["admin", "import", "dolce", "--help"])
    assert result.exit_code == 0
    assert "--source" in result.stdout
    assert "--version" in result.stdout
    assert "--json" in result.stdout


def test_admin_import_dolce_text_output() -> None:
    """Text output covers role / version / source / stats."""
    result = runner.invoke(app, [
        "admin", "import", "dolce",
        "--source", str(FIXTURE_DIR / "dolce_synth.owl"),
        "--version", "synth-test",
    ])
    assert result.exit_code == 0
    assert "role=ontology" in result.stdout
    assert "version=synth-test" in result.stdout
    assert "source=dolce-dul" in result.stdout
    assert "stats:" in result.stdout


def test_admin_import_dolce_json_output_is_valid() -> None:
    """JSON output parses as valid ImportResult shape."""
    result = runner.invoke(app, [
        "admin", "import", "dolce",
        "--source", str(FIXTURE_DIR / "dolce_synth.owl"),
        "--version", "synth-test",
        "--json",
    ])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["role"] == "ontology"
    assert payload["version"] == "synth-test"
    assert payload["source"] == "dolce-dul"
    assert "stats" in payload
    assert isinstance(payload["stats"], dict)


def test_admin_import_oewn_json_output() -> None:
    result = runner.invoke(app, [
        "admin", "import", "oewn",
        "--source", str(FIXTURE_DIR / "oewn_synth.xml"),
        "--json",
    ])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["role"] == "lexicon"
    assert payload["source"] == "oewn"


def test_admin_import_framenet_json_output() -> None:
    result = runner.invoke(app, [
        "admin", "import", "framenet",
        "--source", str(FIXTURE_DIR / "framenet_synth.xml"),
        "--json",
    ])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["role"] == "concepts"
    assert payload["source"] == "framenet"


def test_admin_import_missing_source_exits_nonzero() -> None:
    """Missing --source → exit 2 (Typer usage error)."""
    result = runner.invoke(app, ["admin", "import", "dolce"])
    assert result.exit_code != 0


def test_admin_import_nonexistent_source_exits_nonzero() -> None:
    """Nonexistent --source path → exit 2 (Typer file-validation)."""
    result = runner.invoke(app, [
        "admin", "import", "dolce",
        "--source", "/nonexistent/path/to/dolce.owl",
    ])
    assert result.exit_code != 0
