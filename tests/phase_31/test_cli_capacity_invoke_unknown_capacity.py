"""Phase 31 — invoke verb exit 1 on unknown capacity IRI (--human).

R0 PB-7 + R3 PB-27 — CapacityRegistrationError is an L3 invariant raise
(exit 1), not an envelope failure (exit 3). The capacity simply doesn't
exist; the bound implementation never ran.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_invoke_unknown_capacity_human_exit_1():
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:does.not.exist",
            "--input-json",
            "{}",
        ],
    )
    assert result.exit_code == 1, result.output
    assert "CapacityRegistrationError" in result.output


def test_invoke_unknown_capacity_json_exit_0():
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:does.not.exist",
            "--input-json",
            "{}",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert parsed["error"] == "CapacityRegistrationError"
