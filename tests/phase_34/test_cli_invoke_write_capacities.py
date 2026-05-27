"""Phase 34 — CLI ``mindsos capacity invoke`` for write capacities (R1 PB-E + R2 PB-C)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.commands.capacity import capacity_app


_RUNNER = CliRunner()


def test_cli_invoke_trace_problem_session_none_succeeds():
    """ADR-0080 bootstrap carve-out: scope='global' + session=None works.

    CLI doesn't pass --session-token at Phase 34 (deferred); body sees
    session=None and skips the cap gate; write succeeds.
    """
    inputs = {
        "datastate:problem_trace.record": {
            "trace_id": "t-cli",
            "value": "from CLI",
        }
    }
    result = _RUNNER.invoke(
        capacity_app,
        [
            "invoke",
            "--json",
            "capacity:trace:problem",
            "--input-json",
            json.dumps(inputs),
        ],
    )
    assert result.exit_code == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    out = json.loads(result.stdout)
    assert out["success"] is True
    assert "write_outcome" in out
    assert out["write_outcome"]["iri"] == "problem-trace-v1:entry:t-cli"
    assert out["write_outcome"]["role"] == "problem-trace"
    assert out["write_outcome"]["scope"] == "global"


def test_cli_invoke_consolidate_mm_without_session_yields_value_error():
    """R2 PB-C: scope='local' without --session-token → ValueError envelope.

    Phase 34 CLI doesn't ship --session-token (Phase 30 carry-forward
    still open); consolidate cannot succeed via CLI without it. Test
    confirms the negative-path envelope surface.
    """
    inputs = {
        "datastate:mm.composite_instance": {
            "memory_id": "m1",
            "value": "x",
        }
    }
    result = _RUNNER.invoke(
        capacity_app,
        [
            "invoke",
            "--json",
            "capacity:consolidate:mm",
            "--input-json",
            json.dumps(inputs),
        ],
    )
    # --json always exits 0 per Phase 31's hybrid exit-code rule.
    assert result.exit_code == 0
    out = json.loads(result.stdout)
    assert out["success"] is False
    assert out["error"]["type"] == "ValueError"


def test_cli_invoke_human_render_includes_write_outcome_iri():
    """R1 PB-E: human-render mentions write_outcome.iri when present."""
    inputs = {
        "datastate:problem_trace.record": {
            "trace_id": "t-h",
            "value": "x",
        }
    }
    result = _RUNNER.invoke(
        capacity_app,
        [
            "invoke",
            "capacity:trace:problem",
            "--input-json",
            json.dumps(inputs),
        ],
    )
    assert result.exit_code == 0
    assert "problem-trace-v1:entry:t-h" in result.stdout
    assert "write_outcome.iri" in result.stdout
