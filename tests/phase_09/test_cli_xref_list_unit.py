"""xref-list CLI verb — unit tests (PB-5 + RR-5 + RR-6 + P63)."""

from __future__ import annotations

from typer.testing import CliRunner

from mindsos_cli.commands.persistence import persistence_app


runner = CliRunner()


def test_verb_registered():
    """xref-list is a sub-command of `persistence`."""
    result = runner.invoke(persistence_app, ["xref-list", "--help"])
    assert result.exit_code == 0
    assert "xref-list" in result.stdout.lower() or "xref-list" in (result.stderr or "")


def test_help_lists_4_filter_flags():
    result = runner.invoke(persistence_app, ["xref-list", "--help"])
    assert result.exit_code == 0
    out = result.stdout
    assert "--metagraph" in out
    assert "--source-id" in out
    assert "--target-metagraph" in out
    assert "--target-id" in out
    assert "--ref-type" in out
    assert "--json" in out


def test_metagraph_flag_required():
    """--metagraph M is required (typer enforces)."""
    result = runner.invoke(persistence_app, ["xref-list"])
    # Typer Required arg missing → exit code 2 (typer convention).
    assert result.exit_code != 0
