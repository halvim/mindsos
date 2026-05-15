"""PB-9 A + R4-5 A — `persistence load --metagraph M` summary + --json + --to-json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_load_metagraph_dependent_state_summary(falkor_client, capsys, monkeypatch) -> None:
    """Phase 09 P52 — replaces the Phase 08 R4-5 A 9-line flat summary
    with a single structured ``Dependent state:`` key=value line.

    Renamed from ``test_load_metagraph_9_line_flat_summary``. Tests
    assert by KEY not by line count, so future bucket additions
    (Phase 10 Snapshots / Phase 11 scanner output) extend the same
    line without breaking this test.
    """
    from mindsos_core.models.graph import Graph
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_cli.commands.persistence import _load_metagraph_cmd

    mg = Metagraph(name="cli-load", identity=IdentityRegistry())
    g1 = Graph(name="g1", role="lex", identity=mg.identity)
    mg.add_graph(g1)
    MetagraphRepository(falkor_client).persist(mg)

    monkeypatch.setattr(
        "mindsos_cli.commands.persistence._build_client",
        lambda: falkor_client,
    )
    monkeypatch.setattr(falkor_client, "close", lambda: None)

    _load_metagraph_cmd(
        "cli-load", to_json=False, out_json=False, force=False
    )

    captured = capsys.readouterr()
    out = captured.out
    # Anchor lines unchanged.
    assert "Metagraph: cli-load" in out
    assert f"Metagraph id: {mg.metagraph_id}" in out
    # Phase 09 P52 — single structured key=value line.
    assert "Dependent state:" in out
    assert "graphs=1" in out
    assert "metaedges=0" in out
    assert "metahyperedges=0" in out
    assert "intergraphedges=0" in out
    assert "intergraphhyperedges=0" in out
    assert "xrefs=0" in out
    assert "elementinstances=0" in out
    assert "compositeinstances=0" in out


def test_load_metagraph_json_opt_in_machine_output(falkor_client, capsys, monkeypatch) -> None:
    """--json emits machine-readable JSON instead of 9-line summary."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_cli.commands.persistence import _load_metagraph_cmd

    mg = Metagraph(name="cli-load-json", identity=IdentityRegistry())
    MetagraphRepository(falkor_client).persist(mg)

    monkeypatch.setattr(
        "mindsos_cli.commands.persistence._build_client",
        lambda: falkor_client,
    )
    monkeypatch.setattr(falkor_client, "close", lambda: None)

    _load_metagraph_cmd(
        "cli-load-json", to_json=False, out_json=True, force=False
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["Metagraph"] == "cli-load-json"
    assert payload["Graphs"] == 0


def test_load_metagraph_to_json_writes_fromdb_sibling(
    falkor_client, tmp_path, monkeypatch
) -> None:
    """RR-7 A — --to-json writes ~/.mindsos/metagraph-<name>.fromdb.json."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_cli import state as state_mod
    from mindsos_cli.commands.persistence import _load_metagraph_cmd

    mg = Metagraph(name="rt-fromdb", identity=IdentityRegistry())
    MetagraphRepository(falkor_client).persist(mg)

    monkeypatch.setattr(
        "mindsos_cli.commands.persistence._build_client",
        lambda: falkor_client,
    )
    monkeypatch.setattr(falkor_client, "close", lambda: None)
    monkeypatch.setattr(state_mod, "state_dir", lambda: tmp_path)

    _load_metagraph_cmd(
        "rt-fromdb", to_json=True, out_json=False, force=False
    )

    target = tmp_path / "metagraph-rt-fromdb.fromdb.json"
    assert target.exists()
    payload = json.loads(target.read_text())
    assert payload["name"] == "rt-fromdb"
    assert payload["metagraph_id"] == mg.metagraph_id
