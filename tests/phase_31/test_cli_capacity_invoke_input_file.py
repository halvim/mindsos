"""Phase 31 — invoke verb reads inputs from --input-file."""

from __future__ import annotations

import json
import tempfile

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_invoke_input_file_happy(tmp_path):
    input_path = tmp_path / "inputs.json"
    input_path.write_text('{"datastate:text.raw": "from file"}')
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:text.space_split",
            "--input-file",
            str(input_path),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert parsed["success"] is True
    assert parsed["outputs"]["datastate:text.tokens"] == ["from", "file"]


def test_invoke_input_file_missing_path_human_exit_2():
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:text.space_split",
            "--input-file",
            "/no/such/path.json",
        ],
    )
    assert result.exit_code == 2
    assert "UsageError" in result.output or "UsageError" in (result.stderr or "")
