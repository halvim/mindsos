"""Audit gate blocking finding → FAILED row + EVT_RELEASE_FAILED.

Per PB-20(c) + PB-Z16(a) + ADR-0114 §am3 §4 error_class enum.

Phase 16 ``_score_levenshtein`` operates on ``node_id`` strings; tests
use controlled node_ids via ``inject_pending_node`` so Lev fires
reliably above the 0.85 blocking threshold.
"""

from __future__ import annotations

import json

import pytest

from mindsos_admin.exceptions import BlockingFindingError
from mindsos_server.audit import EVT_RELEASE_FAILED
from mindsos_server.release import release_update


def test_audit_gate_blocking_writes_failed_row(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, inject_pending_node,
):
    """Two near-identical-id pending nodes → intra-pending blocking."""
    # Use near-identical node_ids — Lev ~ 0.93 → blocking (≥ 0.85).
    inject_pending_node(
        pending_global_mg=pending_global_mg,
        node_id="dup-test-aaaaaaaa-0001",
        target_role="ontology",
    )
    inject_pending_node(
        pending_global_mg=pending_global_mg,
        node_id="dup-test-aaaaaaaa-0002",
        target_role="ontology",
    )

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
    assert manifest["included_mutation_ids"] == []
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
    canonical_global_mg, pending_global_mg, inject_pending_node,
):
    """FAILED leaves pending intact per Z2(a) for rerun-recovery."""
    inject_pending_node(
        pending_global_mg=pending_global_mg,
        node_id="leak-test-aaaaaa-0001",
    )
    inject_pending_node(
        pending_global_mg=pending_global_mg,
        node_id="leak-test-aaaaaa-0002",
    )
    pending_ontology = next(
        g for g in pending_global_mg.graphs.values() if g.role == "ontology"
    )
    assert len(pending_ontology.nodes) == 2

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
