"""Per-role MERGE-on-id semantics — rerun is idempotent at FalkorDB level.

Per PB-Z9(a) — pending node_id IS canonical node_id; lifecycle
preserves identity. The Phase 24 v1 in-memory version uses
``add_node`` with the same node_id from pending; Z21.2 + the Z7
suppression set together prevent IdentityError on rerun.

Phase 26 will replace the in-memory add_node with FalkorDB Cypher
MERGE-on-node_id; the test contract is the same: rerun is no-op
at the FalkorDB-graph level if the node already landed.
"""

from __future__ import annotations

import json

from mindsos_admin import propose_for_promotion
from mindsos_server.release import release_update


def test_rerun_does_not_duplicate_canonical(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """SHIPPED then re-propose same content (different node_id) → cross-mg
    blocking finding (no duplicate added per Z9(a)).
    """
    # First ship: A lands in canonical.
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="Original"),
        pending_global_mg=pending_global_mg,
    )
    r1 = release_update(
        seeded_admin, session=admin_session_both,
        canonical_global_mg=canonical_global_mg,
        pending_global_mg=pending_global_mg,
    )
    assert r1.status == "SHIPPED"

    canonical_ontology = next(
        g for g in canonical_global_mg.graphs.values() if g.role == "ontology"
    )
    assert len(canonical_ontology.nodes) == 1

    # Re-propose "Original" — new node_id, identical content.
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="Original"),
        pending_global_mg=pending_global_mg,
    )

    # Second ship: cross-mg blocking; canonical does NOT gain a duplicate.
    from mindsos_admin.exceptions import BlockingFindingError
    import pytest
    with pytest.raises(BlockingFindingError):
        release_update(
            seeded_admin, session=admin_session_both,
            canonical_global_mg=canonical_global_mg,
            pending_global_mg=pending_global_mg,
        )

    # Canonical still has only 1 node — no duplicate via Z9(a) MERGE
    # semantics (here enforced by the audit gate blocking).
    assert len(canonical_ontology.nodes) == 1


def test_pending_node_id_preserved_in_canonical(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """Per Z9(a) — pending node_id IS canonical node_id."""
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="Unique"),
        pending_global_mg=pending_global_mg,
    )
    cur = seeded_admin.execute("SELECT payload_json FROM pending_mutations")
    payload = json.loads(cur.fetchone()[0])
    pending_node_id = payload["node_id"]

    release_update(
        seeded_admin, session=admin_session_both,
        canonical_global_mg=canonical_global_mg,
        pending_global_mg=pending_global_mg,
    )

    canonical_ontology = next(
        g for g in canonical_global_mg.graphs.values() if g.role == "ontology"
    )
    assert pending_node_id in canonical_ontology.nodes
