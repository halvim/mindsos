"""load --metagraph M summary — P52 structured `Dependent state:` line.

Replaces the Phase 08 R4-5 A 9-line flat summary. Phase 09 P52 +
M17: single ``Dependent state:`` line + ``XRefs:`` count included.
"""

from __future__ import annotations

import json

import pytest

from mindsos_core.cypher.builders import build_create_metagraph_anchor

pytestmark = pytest.mark.integration


def test_summary_emits_dependent_state_line(falkor_client, monkeypatch):
    from mindsos_cli.commands import persistence as persistence_mod
    from typer.testing import CliRunner

    q, p = build_create_metagraph_anchor("mg-sum-1", "sum-1", props_json="{}")
    falkor_client.run_query(q, p)
    monkeypatch.setattr(persistence_mod, "_build_client", lambda: falkor_client)
    monkeypatch.setattr(falkor_client, "close", lambda: None)

    runner = CliRunner()
    result = runner.invoke(
        persistence_mod.persistence_app,
        ["load", "--metagraph", "sum-1"],
    )
    assert result.exit_code == 0, result.stdout
    # P52 — single `Dependent state:` line replaces the 9-line list.
    assert "Dependent state:" in result.stdout
    # Includes XRefs count (M17).
    assert "xrefs=" in result.stdout


def test_json_summary_includes_xrefs_key(falkor_client, monkeypatch):
    from mindsos_cli.commands import persistence as persistence_mod
    from typer.testing import CliRunner

    q, p = build_create_metagraph_anchor("mg-sum-2", "sum-2", props_json="{}")
    falkor_client.run_query(q, p)
    monkeypatch.setattr(persistence_mod, "_build_client", lambda: falkor_client)
    monkeypatch.setattr(falkor_client, "close", lambda: None)

    runner = CliRunner()
    result = runner.invoke(
        persistence_mod.persistence_app,
        ["load", "--metagraph", "sum-2", "--json"],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert "XRefs" in payload
    assert payload["XRefs"] == 0
