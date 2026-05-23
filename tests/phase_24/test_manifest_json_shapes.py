"""manifest_json shapes — SHIPPED (PB-22(a)) + FAILED (PB-28(a) + Z7(a))."""

from __future__ import annotations

import json

import pytest

from mindsos_admin import propose_for_promotion
from mindsos_admin.exceptions import BlockingFindingError
from mindsos_server.release import release_update


def test_shipped_manifest_json_shape(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """SHIPPED shape per ADR-0114 §3 — full 5 keys."""
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(),
        pending_global_mg=pending_global_mg,
    )
    result = release_update(
        seeded_admin, session=admin_session_both,
        canonical_global_mg=canonical_global_mg,
        pending_global_mg=pending_global_mg,
    )
    manifest = result.manifest_json
    # PB-22(a) + ADR-0114 §3 SHIPPED keys.
    assert set(manifest.keys()) == {
        "included_mutation_ids",
        "rewrite_map",
        "roles_affected",
        "audit_event_id",
        "shipped_at",
    }
    assert manifest["rewrite_map"] == {}  # empty at admin-direct ATOM
    assert manifest["shipped_at"] is not None
    assert manifest["audit_event_id"] == result.audit_event_id


def test_failed_manifest_json_shape(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """FAILED shape per ADR-0114 §3 + §am3 §1 — includes
    failed_release_canonical_node_ids.
    """
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="Dup"),
        pending_global_mg=pending_global_mg,
    )
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="Dup"),
        pending_global_mg=pending_global_mg,
    )
    with pytest.raises(BlockingFindingError):
        release_update(
            seeded_admin, session=admin_session_both,
            canonical_global_mg=canonical_global_mg,
            pending_global_mg=pending_global_mg,
        )

    # Inspect FAILED manifest_json.
    cur = seeded_admin.execute(
        "SELECT manifest_json FROM releases WHERE status = 'FAILED'"
    )
    manifest = json.loads(cur.fetchone()[0])
    expected_keys = {
        "included_mutation_ids",
        "rewrite_map",
        "roles_affected",
        "failed_at_role",
        "error_class",
        "mutations_attempted_count",
        "audit_event_id",
        "shipped_at",
        "failed_at",
        "failed_release_canonical_node_ids",
    }
    assert set(manifest.keys()) == expected_keys
    assert manifest["shipped_at"] is None
    assert manifest["failed_at"] is not None
    assert manifest["error_class"] == "blocking_similarity_findings"
    assert manifest["included_mutation_ids"] == []
    assert manifest["mutations_attempted_count"] == 2
    # Audit-gate-blocking: NO per-role copies happened, so
    # failed_release_canonical_node_ids is empty.
    assert manifest["failed_release_canonical_node_ids"] == {}
