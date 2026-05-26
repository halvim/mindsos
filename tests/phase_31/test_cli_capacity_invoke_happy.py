"""Phase 31 — `mindsos capacity invoke` happy path (human + json)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_invoke_happy_human():
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:text.space_split",
            "--input-json",
            '{"datastate:text.raw": "hello world"}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert "success" in result.output
    assert "datastate:text.tokens" in result.output


def test_invoke_happy_json():
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:text.space_split",
            "--input-json",
            '{"datastate:text.raw": "hello world"}',
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert parsed["success"] is True
    assert parsed["outputs"]["datastate:text.tokens"] == ["hello", "world"]
    assert parsed["error"] is None
