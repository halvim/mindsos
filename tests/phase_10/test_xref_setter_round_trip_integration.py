"""XRef PX2 setter round-trip vs real FalkorDB."""

from __future__ import annotations

import pytest

from mindsos_core import Graph, Metagraph
from mindsos_core.persistence import MetagraphRepository
from mindsos_core.persistence.bootstrap import bootstrap
from mindsos_core.reconstruction.metagraph_loader import MetagraphLoader
from mindsos_core.reconstruction.xref_loader import XRefLoader

pytestmark = pytest.mark.integration


def _seed_with_xref(client) -> tuple[Metagraph, str]:
    bootstrap(client)
    mg = Metagraph(name="int-xref-test")
    g = Graph(name="g", role="ont")
    mg.add_graph(g)
    n1 = g.add_node(value="a", type_name="Person")
    xref = mg.add_xref(
        source_id=n1.node_id,
        target_metagraph_id="other-mg",
        target_role="ont",
        target_id="tid",
        ref_type="SPECIALISES",
    )
    return mg, xref.xref_id


def _load_with_xrefs(client, mid: str, *, include_deprecated: bool = False) -> Metagraph:
    """Phase 09 idiom — MetagraphLoader.load + XRefLoader.load_into for xref population.

    The after_load observer chain requires explicit ``attach_xref_loader`` on
    the target mg; the fresh mg created inside ``MetagraphLoader.load`` has
    no observers wired, so we call ``XRefLoader.load_into`` directly afterward.
    """
    loaded = MetagraphLoader(client).load(mid, include_deprecated=include_deprecated)
    XRefLoader(client).load_into(loaded)
    return loaded


def test_xref_target_stale_round_trip(falkor_client):
    mg, xid = _seed_with_xref(falkor_client)
    mg.mark_xref_stale(xid)
    MetagraphRepository(falkor_client).persist(mg)
    loaded = _load_with_xrefs(falkor_client, mg.metagraph_id)
    assert loaded.xrefs[xid].target_stale is True


def test_xref_deprecated_at_round_trip(falkor_client):
    mg, xid = _seed_with_xref(falkor_client)
    mg.deprecate_xref(xid)
    MetagraphRepository(falkor_client).persist(mg)
    loaded = _load_with_xrefs(falkor_client, mg.metagraph_id, include_deprecated=True)
    assert loaded.xrefs[xid].deprecated_at is not None


def test_iter_xrefs_filter_includes_stale_excludes_deprecated(falkor_client):
    """target_stale visible by default; deprecated_at filtered."""
    mg, xid = _seed_with_xref(falkor_client)
    mg.mark_xref_stale(xid)
    mg.deprecate_xref(xid)
    MetagraphRepository(falkor_client).persist(mg)
    loaded = _load_with_xrefs(falkor_client, mg.metagraph_id)
    # default include_deprecated=False filters out the xref since deprecated_at!=None
    visible = list(loaded.iter_xrefs())
    assert len(visible) == 0
    full = list(loaded.iter_xrefs(include_deprecated=True))
    assert len(full) == 1
    assert full[0].target_stale is True
