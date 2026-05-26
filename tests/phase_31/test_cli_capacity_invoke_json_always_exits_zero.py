"""Phase 31 — invoke verb --json always exits 0 (R0 PB-7 hybrid lock).

Comprehensive matrix: --json on success, --json on envelope failure,
--json on unknown IRI, --json on usage error — all exit 0 with the
error reified in the JSON payload.

Failure / unknown / envelope cases are covered individually in
test_cli_capacity_invoke_{envelope_failure,unknown_capacity}.py; this
file is the consolidated assertion that exit_code == 0 in all --json
paths.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_json_success_exit_0():
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:text.space_split",
            "--input-json",
            '{"datastate:text.raw": "ok"}',
            "--json",
        ],
    )
    assert result.exit_code == 0


def test_json_envelope_failure_exit_0():
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:text.space_split",
            "--input-json",
            '{"datastate:text.raw": 1}',
            "--json",
        ],
    )
    assert result.exit_code == 0


def test_json_unknown_iri_exit_0():
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:no.such",
            "--input-json",
            "{}",
            "--json",
        ],
    )
    assert result.exit_code == 0


def test_json_mutex_violation_exit_0():
    """--input-json AND --input-file BOTH → exit 0 on --json (UsageError JSON)."""
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:text.space_split",
            "--input-json",
            '{}',
            "--input-file",
            "/dev/null",
            "--json",
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["error"] == "UsageError"
