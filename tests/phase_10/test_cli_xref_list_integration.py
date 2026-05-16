"""CLI xref-list integration vs real FalkorDB — 10-field JSON + table columns."""

from __future__ import annotations

import json

import pytest

from mindsos_core import Graph, Metagraph
from mindsos_core.persistence import MetagraphRepository
from mindsos_core.persistence.bootstrap import bootstrap

pytestmark = pytest.mark.integration


def test_xref_list_json_shows_target_stale_and_deprecated_at(falkor_client, monkeypatch):
    """End-to-end: persist a stale + deprecated xref; CLI JSON shows both."""
    bootstrap(falkor_client)
    mg = Metagraph(name="int-cli-xref")
    g = Graph(name="g", role="ont")
    mg.add_graph(g)
    n1 = g.add_node(value="a", type_name="Person")
    x = mg.add_xref(
        source_id=n1.node_id, target_metagraph_id="other",
        target_role="ont", target_id="tid", ref_type="SPECIALISES",
    )
    mg.mark_xref_stale(x.xref_id)
    mg.deprecate_xref(x.xref_id)
    MetagraphRepository(falkor_client).persist(mg)

    # Monkeypatch the CLI's _build_client to reuse the test fixture's client.
    import mindsos_cli.commands.persistence as pers_mod
    monkeypatch.setattr(pers_mod, "_build_client", lambda: falkor_client)

    # Inhibit the fixture's auto-close at the end of the run.
    original_close = falkor_client.close
    monkeypatch.setattr(falkor_client, "close", lambda: None)

    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(pers_mod.persistence_app, [
        "xref-list", "--metagraph", "int-cli-xref", "--json",
    ])

    # Restore close so the fixture finalizer cleans up.
    monkeypatch.setattr(falkor_client, "close", original_close)

    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert len(parsed) == 1
    row = parsed[0]
    assert row["xref_id"] == x.xref_id
    assert row["target_stale"] is True
    assert row["deprecated_at"] is not None
    # M24 — 10-field shape unconditional
    assert set(row.keys()) == {
        "xref_id", "source_id", "target_metagraph_id", "target_role",
        "target_id", "ref_type", "target_stale", "deprecated_at",
    }
