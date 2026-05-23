"""Happy-path propose_for_promotion (ATOM admin-direct).

Per ADR-0118 + ADR-0114 §1 + Phase 24 design log PB-3(a) + PB-25(a).
"""

from __future__ import annotations

import json

from mindsos_admin import propose_for_promotion
from mindsos_server.audit import EVT_PROMOTION_PROPOSED


def test_propose_writes_pending_mutations_row(
    seeded_admin, admin_session_propose,
    pending_global_mg, atom_proposal_factory,
):
    """Propose writes one pending_mutations row + EVT_PROMOTION_PROPOSED audit."""
    proposal = atom_proposal_factory(
        node_type="Class",
        value="Animal",
        properties={"definition": "Animal"},
        target_role="ontology",
    )

    result = propose_for_promotion(
        seeded_admin,
        session=admin_session_propose,
        proposal=proposal,
        pending_global_mg=pending_global_mg,
    )

    assert len(result.mutation_ids) == 1
    mutation_id = result.mutation_ids[0]

    # pending_mutations row present + correctly shaped.
    cur = seeded_admin.execute(
        "SELECT proposer_admin_user_id, source_user_id, mutation_type, "
        "payload_json, shipped_in_release "
        "FROM pending_mutations WHERE mutation_id = ?",
        (mutation_id,),
    )
    row = cur.fetchone()
    assert row is not None
    proposer, source_user, mutation_type, payload_json, shipped_in_release = row
    assert proposer == "admin"
    assert source_user is None  # v1 admin-direct
    assert mutation_type == "PROMOTION"
    assert shipped_in_release is None  # unshipped

    # payload_json contains the NodeSpec + minted node_id.
    payload = json.loads(payload_json)
    assert payload["kind"] == "ATOM"
    assert "node_id" in payload and len(payload["node_id"]) > 0
    assert payload["node"]["target_role"] == "ontology"
    assert payload["node"]["node_type"] == "Class"
    assert payload["node"]["value"] == "Animal"


def test_propose_adds_node_to_pending_global_mg(
    seeded_admin, admin_session_propose,
    pending_global_mg, atom_proposal_factory,
):
    """In-memory pending_global_mg gains the node per PB-Z21(b)."""
    proposal = atom_proposal_factory(
        node_type="Class", value="Tree", target_role="ontology",
    )
    result = propose_for_promotion(
        seeded_admin,
        session=admin_session_propose,
        proposal=proposal,
        pending_global_mg=pending_global_mg,
    )

    # Find the ontology graph and assert the new node lives there.
    ontology_graph = next(
        g for g in pending_global_mg.graphs.values() if g.role == "ontology"
    )
    assert len(ontology_graph.nodes) == 1

    # node_id matches what's in payload_json
    cur = seeded_admin.execute(
        "SELECT payload_json FROM pending_mutations WHERE mutation_id = ?",
        (result.mutation_ids[0],),
    )
    payload = json.loads(cur.fetchone()[0])
    expected_node_id = payload["node_id"]
    assert expected_node_id in ontology_graph.nodes


def test_propose_writes_evt_promotion_proposed(
    seeded_admin, admin_session_propose,
    pending_global_mg, atom_proposal_factory,
):
    """EVT_PROMOTION_PROPOSED audit row with PB-27(a) payload shape."""
    proposal = atom_proposal_factory(reason="testing batch")
    result = propose_for_promotion(
        seeded_admin,
        session=admin_session_propose,
        proposal=proposal,
        pending_global_mg=pending_global_mg,
    )

    cur = seeded_admin.execute(
        "SELECT actor_user, event, target_user, extra_json "
        "FROM audit WHERE id = ?",
        (result.audit_event_id,),
    )
    row = cur.fetchone()
    actor, event, target, extra_json = row
    assert actor == "admin"
    assert event == EVT_PROMOTION_PROPOSED
    assert target is None
    extra = json.loads(extra_json)
    # PB-27(a) shape: proposer_admin_user_id, mutation_ids, items_count,
    # kinds, roles_affected.
    assert extra["proposer_admin_user_id"] == "admin"
    assert extra["mutation_ids"] == list(result.mutation_ids)
    assert extra["items_count"] == 1
    assert extra["kinds"] == ["ATOM"]
    assert extra["roles_affected"] == ["ontology"]
    assert extra["reason"] == "testing batch"


def test_propose_pending_mutations_auto_increment_order(
    seeded_admin, admin_session_propose,
    pending_global_mg, atom_proposal_factory,
):
    """mutation_id is monotonic AUTOINCREMENT per ADR-0114 §1 + Z6(c) clause 5."""
    p1 = atom_proposal_factory(value="A", target_role="ontology")
    p2 = atom_proposal_factory(value="B", target_role="ontology")

    r1 = propose_for_promotion(
        seeded_admin, session=admin_session_propose,
        proposal=p1, pending_global_mg=pending_global_mg,
    )
    r2 = propose_for_promotion(
        seeded_admin, session=admin_session_propose,
        proposal=p2, pending_global_mg=pending_global_mg,
    )
    assert r1.mutation_ids[0] < r2.mutation_ids[0]


def test_propose_multi_item_batch(
    seeded_admin, admin_session_propose, pending_global_mg,
):
    """Multi-item ATOM batch in one propose call (PB-18(a) + Z6(c) order)."""
    from mindsos_admin import (
        NodeSpec,
        PromotionItem,
        PromotionItemKind,
        PromotionProposal,
    )

    proposal = PromotionProposal(
        items=[
            PromotionItem(
                kind=PromotionItemKind.ATOM,
                node=NodeSpec(
                    node_type="Class", value=f"Node{i}",
                    properties={}, target_role="ontology",
                ),
            )
            for i in range(3)
        ],
    )
    result = propose_for_promotion(
        seeded_admin, session=admin_session_propose,
        proposal=proposal, pending_global_mg=pending_global_mg,
    )
    assert len(result.mutation_ids) == 3
    # mutation_ids are monotonic (AUTOINCREMENT order).
    assert list(result.mutation_ids) == sorted(result.mutation_ids)
