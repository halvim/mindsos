"""Phase 30 — `mindsos capacity find` CLI verb.

Per R2 PB-27(a) + R3 PB-43(a): CLI uses fresh in-memory layer per
invocation; against an empty layer the BFS always exhausts → exit 1.
Per R2 PB-33(a): --json emits verbose Pipeline JSON; default is arrow
chain (which on empty-layer never renders because exit 1 happens
first).
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_find_against_empty_layer_exits_1():
    result = runner.invoke(
        app,
        [
            "capacity",
            "find",
            "--start",
            "datastate:test.input",
            "--target",
            "datastate:test.output",
        ],
    )
    assert result.exit_code == 1


def test_find_against_empty_layer_json_emits_error_payload():
    result = runner.invoke(
        app,
        [
            "capacity",
            "find",
            "--start",
            "datastate:test.input",
            "--target",
            "datastate:test.output",
            "--json",
        ],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout.strip())
    assert payload["error"] == "PipelineNotFoundError"


def test_find_start_equals_target_exits_0():
    """start == target returns empty-steps pipeline; exit 0 + arrow line."""
    result = runner.invoke(
        app,
        [
            "capacity",
            "find",
            "--start",
            "datastate:test.input",
            "--target",
            "datastate:test.input",
        ],
    )
    assert result.exit_code == 0
    assert "already at target" in result.stdout


def test_find_missing_required_arg_exits_2():
    """Typer maps missing required option to exit 2."""
    result = runner.invoke(app, ["capacity", "find", "--start", "datastate:x"])
    assert result.exit_code == 2
