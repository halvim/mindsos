"""End-to-end: remove_graph(force=True) stamps target_stale on incoming XRefs via real DB."""

from __future__ import annotations

import pytest

from mindsos_core import Graph, Metagraph
from mindsos_core.persistence import MetagraphRepository
from mindsos_core.persistence.bootstrap import bootstrap
from mindsos_core.reconstruction.metagraph_loader import MetagraphLoader

pytestmark = pytest.mark.integration


def test_force_true_stamps_target_stale_persists(falkor_client):
    """Phase 10 ADR-0135 §Decision step 3 — verify in-DB after persist."""
    bootstrap(falkor_client)
    mg = Metagraph(name="int-force-stamp")
    g1 = Graph(name="g1", role="ontology")
    g2 = Graph(name="g2", role="lexicon")
    mg.add_graph(g1); mg.add_graph(g2)
    n1 = g1.add_node(value="a", type_name="Person")
    n2 = g2.add_node(value="b", type_name="Person")
    xref = mg.add_xref(
        source_id=n2.node_id,
        target_metagraph_id=mg.metagraph_id,
        target_role="ontology",
        target_id=n1.node_id,
        ref_type="SPECIALISES",
    )

    # Persist clean baseline so xref exists in DB.
    MetagraphRepository(falkor_client).persist(mg)
    assert mg.xrefs[xref.xref_id].target_stale is False

    # force=True path: removes g1, stamps target_stale=True on the surviving xref.
    impact = mg.remove_graph(g1.graph_id, force=True)
    assert impact.proceeded is True
    assert g1.graph_id not in mg.graphs
    assert mg.xrefs[xref.xref_id].target_stale is True

    # Persist the stamp + reload — DB sees the change.
    MetagraphRepository(falkor_client).persist(mg)
    loaded = MetagraphLoader(falkor_client).load(mg.metagraph_id)
    assert loaded.xrefs[xref.xref_id].target_stale is True
