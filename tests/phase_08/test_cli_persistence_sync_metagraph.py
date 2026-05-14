"""PB-8 A + RPB-4 C — `persistence sync --metagraph M [--replace]`."""

from __future__ import annotations

import pytest
import typer

pytestmark = pytest.mark.integration


def test_sync_metagraph_persists_to_falkordb(
    falkor_client, monkeypatch, tmp_path
) -> None:
    """PB-8 A — sync --metagraph M persists state JSON → FalkorDB."""
    import json

    from mindsos_cli import state as state_mod
    from mindsos_cli.commands.persistence import sync_cmd

    # Build a minimal metagraph state file at tmp_path.
    monkeypatch.setattr(state_mod, "state_dir", lambda: tmp_path)
    mg_state = {
        "_state_version": 3,
        "name": "sync-test",
        "metagraph_id": "mid-sync-test",
        "id_strategy": "uuid4",
        "properties": {},
        "schema_name": None,
        "graphs": [],
        "metaedges": [],
        "metahyperedges": [],
        "intergraph_edges": [],
        "intergraph_hyperedges": [],
    }
    (tmp_path / "metagraph-sync-test.json").write_text(json.dumps(mg_state))

    monkeypatch.setattr(
        "mindsos_cli.commands.persistence._build_client",
        lambda: falkor_client,
    )
    monkeypatch.setattr(falkor_client, "close", lambda: None)

    sync_cmd(graph=None, metagraph="sync-test", replace=False)

    # Verify the :Metagraph anchor row landed.
    res = falkor_client.run_query(
        "MATCH (m:Metagraph {name: $name}) RETURN m.id AS mid",
        {"name": "sync-test"},
    )
    assert res.rows
    assert res.rows[0]["mid"] == "mid-sync-test"


def test_sync_metagraph_replace_refuses_on_dependent_instances(
    falkor_client, monkeypatch, tmp_path
) -> None:
    """RPB-4 C — `--replace` refuses on dependent ElementInstance."""
    import json

    from mindsos_cli import state as state_mod
    from mindsos_cli.commands.persistence import sync_cmd

    monkeypatch.setattr(state_mod, "state_dir", lambda: tmp_path)
    mg_state = {
        "_state_version": 3,
        "name": "sync-deps-test",
        "metagraph_id": "mid-deps",
        "id_strategy": "uuid4",
        "properties": {},
        "schema_name": None,
        "graphs": [],
        "metaedges": [],
        "metahyperedges": [],
        "intergraph_edges": [],
        "intergraph_hyperedges": [],
    }
    (tmp_path / "metagraph-sync-deps-test.json").write_text(
        json.dumps(mg_state)
    )

    monkeypatch.setattr(
        "mindsos_cli.commands.persistence._build_client",
        lambda: falkor_client,
    )
    monkeypatch.setattr(falkor_client, "close", lambda: None)

    # Seed a dependent ElementInstance row.
    falkor_client.run_query(
        "CREATE (i:ElementInstance {metagraph_id: $mid, id: 'i1', kind: 'node'})",
        {"mid": "mid-deps"},
    )

    # First, sync without --replace to land the anchor.
    sync_cmd(graph=None, metagraph="sync-deps-test", replace=False)

    # Now --replace should refuse with exit 2.
    # B-08-T8 — typer.Exit (= click.exceptions.Exit) is NOT a SystemExit
    # subclass; pytest.raises(SystemExit) misses it.
    with pytest.raises(typer.Exit) as excinfo:
        sync_cmd(graph=None, metagraph="sync-deps-test", replace=True)
    assert excinfo.value.exit_code == 2
