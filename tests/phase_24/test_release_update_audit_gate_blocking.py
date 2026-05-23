"""Audit gate blocking finding → FAILED row + EVT_RELEASE_FAILED.

Per PB-20(c) + PB-Z16(a) + ADR-0114 §am3 §4 error_class enum.
"""

from __future__ import annotations

import json

import pytest

from mindsos_admin import propose_for_promotion
from mindsos_admin.exceptions import BlockingFindingError
from mindsos_server.audit import EVT_RELEASE_FAILED
from mindsos_server.release import release_update


def test_audit_gate_blocking_writes_failed_row(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """Two identical-content proposals → intra-pending blocking finding."""
    # Propose A.
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="Duplicate", target_role="ontology"),
        pending_global_mg=pending_global_mg,
    )
    # Propose B = identical IRI tail content as A (same value+type).
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="Duplicate", target_role="ontology"),
        pending_global_mg=pending_global_mg,
    )
    # release_update fires intra-pending blocking finding (A vs B).
    with pytest.raises(BlockingFindingError):
        release_update(
            seeded_admin,
            session=admin_session_both,
            canonical_global_mg=canonical_global_mg,
            pending_global_mg=pending_global_mg,
        )

    # FAILED row written.
    cur = seeded_admin.execute(
        "SELECT release_id, status, manifest_json, audit_event_id "
        "FROM releases WHERE status = 'FAILED'"
    )
    row = cur.fetchone()
    assert row is not None
    release_id, status, manifest_str, event_id = row
    assert status == "FAILED"

    manifest = json.loads(manifest_str)
    assert manifest["error_class"] == "blocking_similarity_findings"
    assert manifest["included_mutation_ids"] == []  # FAILED leaves pending
    assert manifest["mutations_attempted_count"] == 2

    # EVT_RELEASE_FAILED audit row with PB-27(a) shape.
    cur = seeded_admin.execute(
        "SELECT event, extra_json FROM audit WHERE id = ?",
        (event_id,),
    )
    event, extra_json = cur.fetchone()
    assert event == EVT_RELEASE_FAILED
    extra = json.loads(extra_json)
    assert extra["release_id"] == release_id
    assert extra["error_class"] == "blocking_similarity_findings"
    assert extra["mutations_attempted_count"] == 2


def test_audit_gate_blocking_leaves_pending_intact(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """FAILED leaves pending intact per Z2(a) for rerun-recovery."""
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="X"),
        pending_global_mg=pending_global_mg,
    )
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="X"),  # duplicate
        pending_global_mg=pending_global_mg,
    )
    pending_ontology = next(
        g for g in pending_global_mg.graphs.values() if g.role == "ontology"
    )
    pending_count_before = len(pending_ontology.nodes)
    assert pending_count_before == 2

    with pytest.raises(BlockingFindingError):
        release_update(
            seeded_admin, session=admin_session_both,
            canonical_global_mg=canonical_global_mg,
            pending_global_mg=pending_global_mg,
        )

    # Pending intact (FAILED path doesn't clear).
    assert len(pending_ontology.nodes) == 2

    # pending_mutations rows still unstamped.
    cur = seeded_admin.execute(
        "SELECT COUNT(*) FROM pending_mutations "
        "WHERE shipped_in_release IS NULL"
    )
    assert cur.fetchone()[0] == 2
