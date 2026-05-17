"""Tier 8 — CLI ``mindsos persistence load --unknown-edges`` flag.

Exercises typer-level option validation and the routing from the CLI
into ``load_graph_with_report`` per Phase 11 step 11. Does NOT spin up
a FalkorDB sidecar — pure CLI/help/usage exercise.
"""

from __future__ import annotations

from typer.testing import CliRunner

from mindsos_cli.commands.persistence import persistence_app


_runner = CliRunner()


def test_load_help_lists_unknown_edges_flag() -> None:
    """``load --help`` mentions the Phase 11 flag."""
    result = _runner.invoke(persistence_app, ["load", "--help"])
    assert result.exit_code == 0
    assert "--unknown-edges" in result.stdout
    # Help mentions the three valid values.
    assert "warn" in result.stdout
    assert "error" in result.stdout
    assert "ignore" in result.stdout


def test_load_rejects_bogus_unknown_edges_value() -> None:
    """``--unknown-edges=bogus`` exits non-zero before reaching the loader."""
    result = _runner.invoke(persistence_app, [
        "load", "--graph", "anything", "--unknown-edges", "bogus",
    ])
    # Pre-loader validation (no FalkorDB needed) → exit 1.
    assert result.exit_code == 1
    combined = (result.stdout + (result.stderr or "")).lower()
    assert "unknown-edges" in combined or "warn|error|ignore" in combined


def test_load_accepts_each_valid_unknown_edges_value() -> None:
    """All three valid values pass parser-side validation."""
    for v in ("warn", "error", "ignore"):
        result = _runner.invoke(persistence_app, [
            "load", "--graph", "name-that-wont-exist", "--unknown-edges", v,
        ])
        # Will exit with a downstream error (no FalkorDB; no such graph),
        # but the early ``--unknown-edges`` validation must NOT reject.
        combined = (result.stdout + (result.stderr or "")).lower()
        assert "unknown-edges must be one of" not in combined, (
            f"value {v!r} should pass parser-side validation"
        )
