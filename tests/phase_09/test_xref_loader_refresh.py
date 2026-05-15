"""XRefLoader refresh — PB-7 + PB-9 + P55 (re-fire after_load + clear-first + dirty)."""

from __future__ import annotations

import pytest

from mindsos_core._observers import _dispatch_after_load
from mindsos_core.cypher.builders import build_create_metagraph_anchor
from mindsos_core.models.xref import XRef
from mindsos_core.persistence.xref_repository import XRefRepository
from mindsos_core.reconstruction.xref_loader import (
    XRefLoader,
    attach_xref_loader,
)

pytestmark = pytest.mark.integration


def _seed_anchor(client, mid: str, name: str) -> None:
    q, p = build_create_metagraph_anchor(mid, name, props_json="{}")
    client.run_query(q, p)


def test_refresh_re_fires_loader_clears_and_reloads(falkor_client):
    """PB-7 + PB-9 — refresh re-loads all XRefs; clear-first overwrites stale."""
    from mindsos_core import Metagraph

    _seed_anchor(falkor_client, "mg-refresh", "refresh")

    mg = Metagraph(name="refresh", metagraph_id="mg-refresh")
    attach_xref_loader(mg)
    mg._persist_client = falkor_client

    # First load: empty DB → mg.xrefs stays empty.
    _dispatch_after_load(mg._after_load_observers, mg)
    assert mg.xrefs == {}

    # Persist an XRef directly via repository (bypasses mg.add_xref).
    XRefRepository(falkor_client).persist(XRef(
        source_metagraph_id="mg-refresh", source_id="s1",
        target_metagraph_id="mg-tgt", target_role="r", target_id="t1",
        ref_type="SPECIALISES", xref_id="xid-after",
    ))

    # Refresh: re-fire after_load → loader picks up the new XRef.
    _dispatch_after_load(mg._after_load_observers, mg)
    assert "xid-after" in mg.xrefs


def test_refresh_clears_dirty_p55(falkor_client):
    """P55 — refresh blanks _xrefs_dirty alongside mg.xrefs."""
    from mindsos_core import Graph, Metagraph

    _seed_anchor(falkor_client, "mg-p55", "p55")
    mg = Metagraph(name="p55", metagraph_id="mg-p55")
    g = Graph(name="g", role="r")
    mg.add_graph(g)
    g.add_node("n1", type_name="C", node_id="n1")

    # Programmatic add (no _persist_client) → marks dirty.
    x = mg.add_xref(source_id="n1", target_metagraph_id="mg-tgt",
                    target_role="r", target_id="t1", ref_type="SPECIALISES")
    assert x.xref_id in mg._xrefs_dirty

    # Refresh via direct loader call (clear-first).
    XRefLoader(falkor_client).load_into(mg)
    assert mg._xrefs_dirty == set()
