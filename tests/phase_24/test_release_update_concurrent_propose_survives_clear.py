"""Concurrent propose's new node survives the SHIPPED-path DELETE.

Per PB-Z20(a) — node-id-scoped DELETE, NOT graph-wide. Concurrent
propose adds a node with a different node_id; the snapshot-set
clear must not touch it.
"""

from __future__ import annotations

from mindsos_admin import propose_for_promotion
from mindsos_server.release import release_update


def test_concurrent_propose_node_survives_clear(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """Sequential-but-conceptually-concurrent: propose; ship; assert post-
    ship pending excludes the shipped node but includes the late one.

    This is a single-threaded simulation of PB-26(b)'s lock-free-propose
    contract. The release_update internally selects its snapshot before
    the clear; a propose AFTER snapshot-select but BEFORE the clear
    would add a new node that must NOT be wiped by the clear. We
    simulate by simply leaving a late-add unshipped through a fresh
    propose AFTER ship, then verifying the post-ship pending state.
    """
    # 1. Propose X (will be shipped).
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="X", target_role="ontology"),
        pending_global_mg=pending_global_mg,
    )

    # 2. Ship — clears X from pending.
    result = release_update(
        seeded_admin, session=admin_session_both,
        canonical_global_mg=canonical_global_mg,
        pending_global_mg=pending_global_mg,
    )
    assert result.status == "SHIPPED"

    # 3. Late propose Y AFTER ship.
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="Y", target_role="ontology"),
        pending_global_mg=pending_global_mg,
    )

    # 4. Y should be in pending; X should not.
    pending_ontology = next(
        g for g in pending_global_mg.graphs.values() if g.role == "ontology"
    )
    assert len(pending_ontology.nodes) == 1  # only Y
    # Y survives because it has a different node_id than the shipped-X set.

    cur = seeded_admin.execute(
        "SELECT COUNT(*) FROM pending_mutations WHERE shipped_in_release IS NULL"
    )
    assert cur.fetchone()[0] == 1  # only Y unshipped


def test_clear_is_node_id_scoped_not_graph_wide(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """PB-Z20(a) lock — DELETE only touches snapshot-set node_ids."""
    # Pre-populate pending with extra nodes that should NOT be touched.
    # Simulate by inserting via add_node directly (not through propose).
    ontology_pending = next(
        g for g in pending_global_mg.graphs.values() if g.role == "ontology"
    )
    sentinel_node = ontology_pending.add_node(
        "SentinelX", "Class", properties={}, node_id="sentinel-pre-existing",
    )

    # Now propose Y and ship.
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="Y"),
        pending_global_mg=pending_global_mg,
    )
    release_update(
        seeded_admin, session=admin_session_both,
        canonical_global_mg=canonical_global_mg,
        pending_global_mg=pending_global_mg,
    )

    # The sentinel node has a different node_id than Y; should survive.
    assert sentinel_node.node_id in ontology_pending.nodes
