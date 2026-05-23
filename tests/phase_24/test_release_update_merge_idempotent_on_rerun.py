"""Per-role MERGE-on-id semantics — rerun is idempotent at FalkorDB level.

Per PB-Z9(a) — pending node_id IS canonical node_id; lifecycle
preserves identity. The Phase 24 v1 in-memory version uses
``add_node`` with the same node_id from pending; Z21.2 + the Z7
suppression set together prevent IdentityError on rerun.

Phase 26 will replace the in-memory add_node with FalkorDB Cypher
MERGE-on-node_id; the test contract is the same: rerun is no-op
at the FalkorDB-graph level if the node already landed.

Uses controlled node_ids via ``inject_pending_node`` /
``inject_canonical_node`` so similarity scores fire reliably.
"""

from __future__ import annotations

import pytest

from mindsos_admin.exceptions import BlockingFindingError
from mindsos_server.release import release_update


def test_rerun_does_not_duplicate_canonical(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg,
    inject_pending_node, inject_canonical_node,
):
    """Pre-shipped node in canonical + near-identical-id pending →
    cross-mg blocking; canonical does NOT gain a duplicate.
    """
    # Pre-seed canonical (as if a prior release shipped this).
    inject_canonical_node(
        canonical_global_mg=canonical_global_mg,
        node_id="orig-test-aaaaa-0001",
        value="Original",
        target_role="ontology",
    )
    canonical_ontology = next(
        g for g in canonical_global_mg.graphs.values() if g.role == "ontology"
    )
    assert len(canonical_ontology.nodes) == 1

    # Now stage a near-identical-id pending mutation.
    inject_pending_node(
        pending_global_mg=pending_global_mg,
        node_id="orig-test-aaaaa-0002",
        value="Original",
        target_role="ontology",
    )

    # Cross-mg blocking — canonical does NOT gain a second node.
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
    """Per Z9(a) — pending node_id IS canonical node_id.

    Single-propose happy path (no duplicates) — Lev score on the
    UUID against any other content is near 0, so no blocking finding;
    ship succeeds; canonical gains the SAME node_id that pending had.
    """
    import json
    from mindsos_admin import propose_for_promotion

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
