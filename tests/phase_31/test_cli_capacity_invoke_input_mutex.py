"""Phase 31 — invoke verb: --input-json XOR --input-file (R1 PB-14)."""

from __future__ import annotations

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_both_flags_human_exit_2():
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:text.space_split",
            "--input-json",
            "{}",
            "--input-file",
            "/dev/null",
        ],
    )
    assert result.exit_code == 2
    assert "mutually exclusive" in result.output.lower() or "mutually exclusive" in (result.stderr or "").lower()
