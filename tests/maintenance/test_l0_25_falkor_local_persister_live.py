"""MAINTENANCE_CHAT M2 (L0-25) — FalkorDBLocalPersister live round-trip.

Phase 44 PR1.2 shipped :class:`FalkorDBLocalPersister` with
``InMemoryClient`` unit tests only (``tests/phase_44/test_falkor_persister.py``);
the save→load round-trip and the scoped ``metagraph_id``-keyed delete were
never exercised against a live FalkorDB. These tests close that gap.

Uses the ``tests/_shared`` ``falkor_client`` fixture (per-test fresh
``test_<uuid8>`` graph; skips without a sidecar) + ``assert_metagraphs_equal``
(Phase 08 reconstruction-fidelity helper).

Scope note (L0-25 — CLOSED at Phase 51): the sweep-completeness audit routed
here by MAINTENANCE_CHAT M2 ran at Phase 51 (WSD-1) over every builder in
``cypher/builders.py``; the sweep is complete for owner-scoped rows, the
orphan-scan below is CONTRACT (xfail removed), and inbound XRefs are pinned
as by-design survivors (ADR-0135 ``target_stale`` model). Audit record:
``PHASE_51_DESIGN_LOG.md``.
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture
from tests._shared.metagraph_equality import assert_metagraphs_equal

pytestmark = pytest.mark.integration


def _build_local(user_id: str):
    """A Local with enough shape to make round-trip + delete meaningful:
    two graphs (primitive-valued nodes, an edge, a hyperedge) + one
    metaedge + one metahyperedge. Node values here stay primitive;
    structured values are in contract since Phase 50 shipped ADR-0182
    and are exercised by ``test_live_structured_value_round_trip``.
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


def test_live_structured_value_round_trip(falkor_client) -> None:  # noqa: F811
    """ADR-0182 (Phase 50): dict/list node values survive save → load.

    Closes the PB-RT gap that descoped the Phase 49 live episode flush:
    a structured 6-field-style dict value JSON-encodes into the node's
    ``_value_json`` column on persist (rule 2), decodes back as
    ``value`` on load (rule 3), never leaks into the user-property bag,
    and co-resident primitive values stay on the untouched fast path
    (rule 1).
    """
    from mindsos_core import Metagraph
    from mindsos_core.models.graph import Graph

    persister = _persister(falkor_client)
    mg = Metagraph(name="local_knowledge:carol")
    g = mg.add_graph(Graph(name="carol-notes", role="episodic_memories"))
    structured = {
        "task_pattern_iri": "tp:demo",
        "chain": {"hints": ["h1", "h2"], "plan_depth": 2},
        "outcome": None,
        "scores": [0.5, 1.0],
    }
    n_dict = g.add_node(structured, "Episode", properties={"user_key": "kept"})
    n_list = g.add_node([1, "two", {"three": 3}], "Episode")
    n_prim = g.add_node("plain", "Episode")
    persister.save("carol", mg)

    loaded = persister.load("carol")
    assert loaded is not None
    assert_metagraphs_equal(mg, loaded)
    (lg,) = loaded.graphs.values()
    assert lg.nodes[n_dict.node_id].value == structured
    assert lg.nodes[n_list.node_id].value == [1, "two", {"three": 3}]
    assert lg.nodes[n_prim.node_id].value == "plain"
    assert lg.nodes[n_dict.node_id].properties.get("user_key") == "kept"
    assert "_value_json" not in lg.nodes[n_dict.node_id].properties

    # Idempotent re-save (MERGE-safe) keeps the pair consistent.
    persister.save("carol", loaded)
    reloaded = persister.load("carol")
    assert reloaded is not None
    assert reloaded.graphs and (
        next(iter(reloaded.graphs.values())).nodes[n_dict.node_id].value
        == structured
    )


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


def test_live_delete_leaves_no_orphans(falkor_client) -> None:  # noqa: F811
    """After delete('alice'), no alice-OWNED row survives (CONTRACT).

    Phase 51 (WSD-1) closes the L0-25 sweep-completeness audit; the
    xfail marker is removed — a pass is contract, not evidence. Audit
    record: ``PHASE_51_DESIGN_LOG.md`` §audit. Per-kind grounding
    (``cypher/builders.py``): nodes/edges/hyperedges die via the
    ``IN_GRAPH`` sweep (edges with their endpoints); metaedges are
    Graph→Graph rels and die with the graphs; metahyperedges,
    intergraph hyperedges, and WALEntries are ``IN_METAGRAPH``
    satellites of the anchor; tombstones are graph-scoped by
    construction (P69 A); outbound XRefs are swept by
    ``source_metagraph_id`` (and are ``XREF_OF`` satellites besides).

    This test seeds every kind the builders can attach to a Local —
    including a tombstone row and an outbound XRef, which
    ``_build_local`` alone does not produce — then asserts zero
    alice-owned leftovers across ALL ownership columns.
    """
    from mindsos_core.cypher.builders import build_create_tombstone, build_create_xref

    persister = _persister(falkor_client)
    alice = _build_local("alice")
    persister.save("alice", alice)

    mid = alice.metagraph_id
    gids = [g.graph_id for g in alice.graphs.values()]

    # Seed the row kinds the round-trip metagraph doesn't carry:
    # a tombstone (removal event in alice's first graph) ...
    q, params = build_create_tombstone(
        graph_id=gids[0], element_id="node:ghost", element_kind="node",
        removed_by="alice",
    )
    falkor_client.run_query(q, params)
    # ... and an OUTBOUND XRef (alice → elsewhere; swept with alice).
    q, params = build_create_xref(
        xref_id="xref:alice-out",
        source_metagraph_id=mid,
        source_id="node:src",
        target_metagraph_id="mg:other",
        target_role="episodic_memories",
        target_id="node:tgt",
        ref_type="REFERS_TO",
        properties={},
    )
    falkor_client.run_query(q, params)

    assert persister.delete("alice") is True

    leftovers = falkor_client.run_query(
        "MATCH (n) WHERE n.metagraph_id = $mid OR n.graph_id IN $gids "
        "OR n.source_metagraph_id = $mid RETURN count(n) AS n",
        {"mid": mid, "gids": gids},
    ).first()["n"]
    assert leftovers == 0, f"{leftovers} orphaned rows after scoped delete"


def test_live_delete_spares_inbound_xrefs_by_design(falkor_client) -> None:  # noqa: F811
    """An INBOUND XRef (bob's row targeting alice) SURVIVES alice's delete.

    Contract pin, not a gap (Phase 51 L0-25 audit): the row is owned by
    bob's metagraph — sweeping it from alice's delete would mutate
    another metagraph outside its mutex and bypass its WAL. Dangling
    targets are the ADR-0135 ``target_stale`` model's job
    (``build_set_xref_target_stale``); stamping at referent-delete time
    is a ledgered enhancement (L0_FUTURE_WORK; trigger: first
    cross-user XRef consumer), not part of the scoped-delete contract.
    """
    from mindsos_core.cypher.builders import build_create_xref

    persister = _persister(falkor_client)
    alice = _build_local("alice")
    bob = _build_local("bob")
    persister.save("alice", alice)
    persister.save("bob", bob)

    q, params = build_create_xref(
        xref_id="xref:bob-in",
        source_metagraph_id=bob.metagraph_id,
        source_id="node:bobsrc",
        target_metagraph_id=alice.metagraph_id,
        target_role="episodic_memories",
        target_id="node:alicetgt",
        ref_type="REFERS_TO",
        properties={},
    )
    falkor_client.run_query(q, params)

    assert persister.delete("alice") is True

    survivor = falkor_client.run_query(
        "MATCH (x:XRef {id: 'xref:bob-in'}) "
        "RETURN x.target_metagraph_id AS tmid",
    ).first()
    assert survivor is not None, "inbound XRef was wrongly swept"
    assert survivor["tmid"] == alice.metagraph_id  # dangling by design
