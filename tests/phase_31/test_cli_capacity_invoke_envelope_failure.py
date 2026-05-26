"""Phase 31 — invoke verb exit 3 on envelope failure (--human).

R0 PB-7 hybrid lock: --human exits 3 when InvocationResult.success=False;
--json exits 0 always (envelope's success bool carries the failure signal).

The bound implementation for text.space_split raises TypeError on non-str
input (per text.py _space_split body). Drive a TypeError by passing an
int as the text.raw value → invoke envelope success=False → exit 3.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_invoke_envelope_failure_human_exit_3():
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:text.space_split",
            "--input-json",
            '{"datastate:text.raw": 42}',  # int triggers TypeError
        ],
    )
    assert result.exit_code == 3, result.output
    assert "FAILED" in result.output
    assert "TypeError" in result.output


def test_invoke_envelope_failure_json_exit_0():
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:text.space_split",
            "--input-json",
            '{"datastate:text.raw": 42}',
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert parsed["success"] is False
    assert parsed["error"]["type"] == "TypeError"
    assert "str" in parsed["error"]["message"]
