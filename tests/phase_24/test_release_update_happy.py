"""release_update happy path — one pending → SHIPPED row + canonical mutated.

Per ADR-0118 §"Decision" §2 + ADR-0114 §3 SHIPPED manifest_json shape.
"""

from __future__ import annotations

import json

from mindsos_admin import propose_for_promotion
from mindsos_server.audit import EVT_RELEASE_SHIPPED
from mindsos_server.release import release_update


def test_release_update_one_pending_ships(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """One propose → release_update → SHIPPED row + canonical has the node."""
    # 1. Propose.
    proposal = atom_proposal_factory(
        node_type="Class", value="Person", target_role="ontology",
    )
    propose_result = propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=proposal, pending_global_mg=pending_global_mg,
    )
    pending_node_id = next(iter([
        nid for g in pending_global_mg.graphs.values() if g.role == "ontology"
        for nid in g.nodes
    ]))

    # 2. Ship.
    result = release_update(
        seeded_admin,
        session=admin_session_both,
        canonical_global_mg=canonical_global_mg,
        pending_global_mg=pending_global_mg,
    )

    # 3. Assertions.
    assert result.status == "SHIPPED"
    assert result.mutations_shipped_count == 1
    assert "ontology" in result.roles_affected
    assert result.error_class is None

    # 3a. Canonical gained the node.
    canonical_ontology = next(
        g for g in canonical_global_mg.graphs.values() if g.role == "ontology"
    )
    assert pending_node_id in canonical_ontology.nodes

    # 3b. Pending cleared per PB-Z8(a).
    pending_ontology = next(
        g for g in pending_global_mg.graphs.values() if g.role == "ontology"
    )
    assert pending_node_id not in pending_ontology.nodes
    assert len(pending_ontology.nodes) == 0

    # 3c. pending_mutations stamped.
    cur = seeded_admin.execute(
        "SELECT shipped_in_release FROM pending_mutations "
        "WHERE mutation_id = ?",
        (propose_result.mutation_ids[0],),
    )
    assert cur.fetchone()[0] == result.release_id

    # 3d. releases row written + SHIPPED.
    cur = seeded_admin.execute(
        "SELECT status, manifest_json, parent_release_id, audit_event_id "
        "FROM releases WHERE release_id = ?",
        (result.release_id,),
    )
    status, manifest_str, parent_id, event_id = cur.fetchone()
    assert status == "SHIPPED"
    assert parent_id is None  # first release
    manifest = json.loads(manifest_str)
    assert manifest["included_mutation_ids"] == [propose_result.mutation_ids[0]]
    assert manifest["roles_affected"] == ["ontology"]
    assert manifest["rewrite_map"] == {}

    # 3e. EVT_RELEASE_SHIPPED audit row.
    cur = seeded_admin.execute(
        "SELECT event, extra_json FROM audit WHERE id = ?",
        (event_id,),
    )
    event, extra_json = cur.fetchone()
    assert event == EVT_RELEASE_SHIPPED
    extra = json.loads(extra_json)
    assert extra["release_id"] == result.release_id
    assert extra["mutations_shipped_count"] == 1
    assert extra["roles_affected"] == ["ontology"]
    assert extra["parent_release_id"] is None


def test_release_update_parent_release_id_chain(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """Second SHIPPED release.parent_release_id == first SHIPPED's release_id."""
    # First ship.
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="A"),
        pending_global_mg=pending_global_mg,
    )
    r1 = release_update(
        seeded_admin, session=admin_session_both,
        canonical_global_mg=canonical_global_mg,
        pending_global_mg=pending_global_mg,
    )
    # Second ship.
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="B"),
        pending_global_mg=pending_global_mg,
    )
    r2 = release_update(
        seeded_admin, session=admin_session_both,
        canonical_global_mg=canonical_global_mg,
        pending_global_mg=pending_global_mg,
    )
    assert r2.parent_release_id == r1.release_id
