"""Phase 30 — `mindsos capacity problem-trace tail` CLI verb.

CLI is fresh in-memory per invocation → sink is always empty at
Phase 30. Verb exists to lock the surface; a real consumer arrives
when CLI gets stateful (Phase 31+ Falkor-backed bootstrap; R2 PB-27).
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_tail_empty_layer_returns_no_records_human():
    result = runner.invoke(app, ["capacity", "problem-trace", "tail"])
    assert result.exit_code == 0
    assert "no problem-trace records" in result.stdout


def test_tail_empty_layer_returns_empty_json_list():
    result = runner.invoke(app, ["capacity", "problem-trace", "tail", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip())
    assert payload == []


def test_tail_respects_limit_flag():
    result = runner.invoke(
        app,
        ["capacity", "problem-trace", "tail", "--limit", "5", "--json"],
    )
    assert result.exit_code == 0
    # Empty sink at Phase 30; just confirm the verb accepts --limit.
    assert json.loads(result.stdout.strip()) == []
