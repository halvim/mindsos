"""Phase 31 — invoke verb exit 2 on Typer usage error.

Missing required argument (no IRI) → Typer raises usage error → exit 2.
"""

from __future__ import annotations

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_invoke_no_args_exit_2():
    result = runner.invoke(app, ["capacity", "invoke"])
    assert result.exit_code == 2


def test_invoke_iri_but_no_input_flags_exit_2():
    """Missing both --input-json and --input-file → exit 2 (manual usage check)."""
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:text.space_split",
        ],
    )
    assert result.exit_code == 2
    assert "exactly one" in result.output.lower() or "exactly one" in (result.stderr or "").lower()
