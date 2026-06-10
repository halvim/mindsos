"""MAINTENANCE_CHAT M2 (L0-25) — FalkorDBLocalPersister live round-trip.

Phase 44 PR1.2 shipped :class:`FalkorDBLocalPersister` with
``InMemoryClient`` unit tests only (``tests/phase_44/test_falkor_persister.py``);
the save→load round-trip and the scoped ``metagraph_id``-keyed delete were
never exercised against a live FalkorDB. These tests close that gap.

Uses the ``tests/_shared`` ``falkor_client`` fixture (per-test fresh
``test_<uuid8>`` graph; skips without a sidecar) + ``assert_metagraphs_equal``
(Phase 08 reconstruction-fidelity helper).

Scope note (L0-25 split): the delete's metaedge/metahyperedge/XRef sweep is a
best-effort first cut (``PHASE_44_DESIGN_LOG.md §7``). The orphan-scan test
below covers the in-Local element kinds it saves (nodes, edges, hyperedge,
metaedge, metahyperedge); the *full* sweep-completeness audit — XRef variants,
tombstones, cross-metagraph satellites — is routed to WSD installation per
the MAINTENANCE_CHAT_LOG M2 decision.
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture
from tests._shared.metagraph_equality import assert_metagraphs_equal

pytestmark = pytest.mark.integration


def _build_local(user_id: str):
    """A Local with enough shape to make round-trip + delete meaningful:
    two graphs (primitive-valued nodes, an edge, a hyperedge) + one
    metaedge + one metahyperedge. Node values stay primitive per the
    L0-26 node-value serialization gap (PB-RT) — structured values are
    out of contract until the L0-26 ADR's first consumer ships.
    """
    from mindsos_core import Metagraph
    from mindsos_core.models.graph import Graph

    mg = Metagraph(name=f"local_knowledge:{user_id}")
    g1 = mg.add_graph(Graph(name=f"{user_id}-notes", role="episodic_memories"))
    n1 = g1.add_node("alpha", "Concept")
    n2 = g1.add_node(42, "Concept")
    n3 = g1.add_node("gamma", "Concept")
    g1.add_edge(n1, n2, "RELATES_TO", label="a->b")
    g1.add_hyperedge([n1, n2, n3], "GROUPS", label="trio")
    g2 = mg.add_graph(Graph(name=f"{user_id}-state", role="capacity-state"))
    g2.add_node("delta", "State")
    mg.add_metaedge(g1.graph_id, g2.graph_id, "DERIVES_FROM", label="m1")
    mg.add_metahyperedge(
        [g1.graph_id, g2.graph_id], type_name="BUNDLES", label="mh1"
    )
    return mg


def _persister(client):
    from mindsos_server.persistence.local_persister import FalkorDBLocalPersister

    return FalkorDBLocalPersister(client)


def test_live_save_load_round_trip(falkor_client) -> None:  # noqa: F811
    """save → load through a live graph reconstructs an equal Metagraph."""
    persister = _persister(falkor_client)
    original = _build_local("alice")
    persister.save("alice", original)

    loaded = persister.load("alice")
    assert loaded is not None
    assert_metagraphs_equal(original, loaded)

    # Idempotent re-save (MERGE-safe per Phase 26a R7-F1) then re-load.
    persister.save("alice", original)
    reloaded = persister.load("alice")
    assert reloaded is not None
    assert_metagraphs_equal(original, reloaded)


def test_live_load_missing_returns_none(falkor_client) -> None:  # noqa: F811
    assert _persister(falkor_client).load("nobody") is None


def test_live_scoped_delete_spares_coresidents(falkor_client) -> None:  # noqa: F811
    """delete('alice') removes alice's Local only — the co-resident Global
    and bob's Local survive byte-equal (a blanket DETACH DELETE would not).
    """
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_knowledge.knowledge_layer import KnowledgeLayer

    persister = _persister(falkor_client)

    # Co-residents in the SAME FalkorDB graph: the Global pair + two Locals.
    kl = KnowledgeLayer.bootstrap()
    global_mg = kl.global_metagraph()
    MetagraphRepository(falkor_client).persist(global_mg)
    alice = _build_local("alice")
    bob = _build_local("bob")
    persister.save("alice", alice)
    persister.save("bob", bob)

    assert persister.delete("alice") is True
    # Idempotent: second delete finds nothing.
    assert persister.delete("alice") is False
    assert persister.load("alice") is None

    # Co-residents untouched.
    bob_loaded = persister.load("bob")
    assert bob_loaded is not None
    assert_metagraphs_equal(bob, bob_loaded)
    from mindsos_core.reconstruction import MetagraphLoader

    loader = MetagraphLoader(falkor_client)
    global_id = loader.find_by_name(global_mg.name)
    assert global_id is not None
    assert_metagraphs_equal(global_mg, loader.load(global_id))


@pytest.mark.xfail(
    strict=False,
    reason="L0-25: the delete sweep is a best-effort first cut "
    "(PHASE_44_DESIGN_LOG.md §7); completeness audit routed to WSD "
    "installation. A pass here is evidence, not yet contract.",
)
def test_live_delete_leaves_no_orphans(falkor_client) -> None:  # noqa: F811
    """After delete('alice'), no row still references alice's metagraph_id
    or her contained graph_ids (sweep-completeness probe — xfail-tolerant)."""
    persister = _persister(falkor_client)
    alice = _build_local("alice")
    persister.save("alice", alice)

    mid = alice.metagraph_id
    gids = [g.graph_id for g in alice.graphs.values()]
    assert persister.delete("alice") is True

    leftovers = falkor_client.run_query(
        "MATCH (n) WHERE n.metagraph_id = $mid OR n.graph_id IN $gids "
        "OR n.source_metagraph_id = $mid RETURN count(n) AS n",
        {"mid": mid, "gids": gids},
    ).first()["n"]
    assert leftovers == 0, f"{leftovers} orphaned rows after scoped delete"
