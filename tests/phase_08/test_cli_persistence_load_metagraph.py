"""PB-9 A + R4-5 A — `persistence load --metagraph M` summary + --json + --to-json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_load_metagraph_9_line_flat_summary(falkor_client, capsys, monkeypatch) -> None:
    """R4-5 A — 9-line flat key:value summary shape."""
    from mindsos_core.models.graph import Graph
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_cli.commands.persistence import _load_metagraph_cmd

    mg = Metagraph(name="cli-load", identity=IdentityRegistry())
    g1 = Graph(name="g1", role="lex", identity=mg.identity)
    mg.add_graph(g1)
    MetagraphRepository(falkor_client).persist(mg)

    # Monkeypatch _build_client to return the live falkor_client fixture.
    monkeypatch.setattr(
        "mindsos_cli.commands.persistence._build_client",
        lambda: falkor_client,
    )

    # Disable client.close() in _load_metagraph_cmd (we're reusing the
    # falkor_client fixture; closing breaks the fixture teardown).
    monkeypatch.setattr(falkor_client, "close", lambda: None)

    _load_metagraph_cmd(
        "cli-load", to_json=False, out_json=False, force=False
    )

    captured = capsys.readouterr()
    out = captured.out
    # 9 key:value lines per R4-5 A.
    assert "Metagraph: cli-load" in out
    assert f"Metagraph id: {mg.metagraph_id}" in out
    assert "Graphs: 1" in out
    assert "MetaEdges: 0" in out
    assert "MetaHyperEdges: 0" in out
    assert "IntergraphEdges: 0" in out
    assert "IntergraphHyperEdges: 0" in out
    assert "ElementInstances: 0" in out
    assert "CompositeInstances: 0" in out


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
