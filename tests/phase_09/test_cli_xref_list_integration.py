"""xref-list CLI verb — integration tests (P63 direct-DB query)."""

from __future__ import annotations

import json

import pytest

from mindsos_core.cypher.builders import build_create_metagraph_anchor
from mindsos_core.models.xref import XRef
from mindsos_core.persistence.xref_repository import XRefRepository

pytestmark = pytest.mark.integration


def _seed(falkor_client, mid: str, name: str, *, n_xrefs: int = 3) -> None:
    q, p = build_create_metagraph_anchor(mid, name, props_json="{}")
    falkor_client.run_query(q, p)
    repo = XRefRepository(falkor_client)
    for i in range(n_xrefs):
        repo.persist(XRef(
            source_metagraph_id=mid, source_id=f"s{i}",
            target_metagraph_id="mg-tgt", target_role="lex",
            target_id=f"t{i}", ref_type="SPECIALISES",
            xref_id=f"xid-{name}-{i}",
        ))


def test_list_all_xrefs_for_metagraph(falkor_client, monkeypatch):
    from mindsos_cli.commands import persistence as persistence_mod

    _seed(falkor_client, "mg-list-1", "list-1")
    monkeypatch.setattr(persistence_mod, "_build_client", lambda: falkor_client)
    monkeypatch.setattr(falkor_client, "close", lambda: None)

    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(
        persistence_mod.persistence_app,
        ["xref-list", "--metagraph", "list-1", "--json"],
    )
    assert result.exit_code == 0, result.stdout
    rows = json.loads(result.stdout)
    assert len(rows) == 3
    keys = set(rows[0].keys())
    assert {"xref_id", "source_id", "target_metagraph_id",
            "target_role", "target_id", "ref_type"} <= keys


def test_list_filters_by_source_id(falkor_client, monkeypatch):
    from mindsos_cli.commands import persistence as persistence_mod

    _seed(falkor_client, "mg-list-2", "list-2", n_xrefs=3)
    monkeypatch.setattr(persistence_mod, "_build_client", lambda: falkor_client)
    monkeypatch.setattr(falkor_client, "close", lambda: None)

    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(
        persistence_mod.persistence_app,
        ["xref-list", "--metagraph", "list-2",
         "--source-id", "s1", "--json"],
    )
    assert result.exit_code == 0
    rows = json.loads(result.stdout)
    assert len(rows) == 1
    assert rows[0]["source_id"] == "s1"


def test_unknown_metagraph_exits_2(falkor_client, monkeypatch):
    from mindsos_cli.commands import persistence as persistence_mod

    monkeypatch.setattr(persistence_mod, "_build_client", lambda: falkor_client)
    monkeypatch.setattr(falkor_client, "close", lambda: None)

    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(
        persistence_mod.persistence_app,
        ["xref-list", "--metagraph", "ghost-mg"],
    )
    assert result.exit_code == 2
