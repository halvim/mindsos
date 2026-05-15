"""sync --metagraph M dependent-state patch — M11 (source_metagraph_id check)."""

from __future__ import annotations

import json

import pytest
import typer

from mindsos_core.cypher.builders import build_create_metagraph_anchor
from mindsos_core.models.xref import XRef
from mindsos_core.persistence.xref_repository import XRefRepository

pytestmark = pytest.mark.integration


def test_dependent_state_check_finds_xref_via_source_metagraph_id(
    falkor_client, monkeypatch, tmp_path
):
    """M11 — _metagraph_has_dependent_state queries source_metagraph_id (not metagraph_id).

    Seeds a real :XRef row using the v3-baseline ``source_metagraph_id``
    field, then runs sync --metagraph --replace and confirms the
    dependent-state check refuses with exit 2 (the XRef row was found).
    """
    from mindsos_cli import state as state_mod
    from mindsos_cli.commands.persistence import sync_cmd

    monkeypatch.setattr(state_mod, "state_dir", lambda: tmp_path)
    mg_state = {
        "_state_version": 4,
        "name": "sync-deps-xref",
        "metagraph_id": "mid-deps-xref",
        "id_strategy": "uuid4",
        "properties": {},
        "schema_name": None,
        "graphs": [],
        "metaedges": [],
        "metahyperedges": [],
        "intergraph_edges": [],
        "intergraph_hyperedges": [],
        "xrefs": [],
    }
    (tmp_path / "metagraph-sync-deps-xref.json").write_text(json.dumps(mg_state))

    monkeypatch.setattr(
        "mindsos_cli.commands.persistence._build_client",
        lambda: falkor_client,
    )
    monkeypatch.setattr(falkor_client, "close", lambda: None)

    # Seed the anchor + a real XRef row with source_metagraph_id (M11
    # patched query field).
    q, p = build_create_metagraph_anchor("mid-deps-xref", "sync-deps-xref",
                                         props_json="{}")
    falkor_client.run_query(q, p)
    XRefRepository(falkor_client).persist(XRef(
        source_metagraph_id="mid-deps-xref", source_id="any",
        target_metagraph_id="mg-tgt", target_role="r", target_id="t",
        ref_type="SPECIALISES", xref_id="xid-deps",
    ))

    # --replace MUST refuse with exit 2 (XRef detected as dependent).
    with pytest.raises(typer.Exit) as excinfo:
        sync_cmd(graph=None, metagraph="sync-deps-xref", replace=True)
    assert excinfo.value.exit_code == 2
