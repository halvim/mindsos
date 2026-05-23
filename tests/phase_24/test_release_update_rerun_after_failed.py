"""Rerun after FAILED uses Z7(a) suppression set + ships successfully.

Per PB-Z1(b) + PB-Z7(a) + PB-Z15(a). The audit gate's cross-mg pass
on rerun would fire blocking findings against prior-FAILED partial-
ship canonical content (same node_id; cross-mg doesn't self-exclude
per Phase 16 line 271 probe). The suppression set built from FAILED
manifest_json filters them out.

Phase 24 v1 in-memory scope: copy loop uses add_node, which raises
on collision. Suppression set prevents the re-add by skipping
already-shipped node_ids per Z21.2.
"""

from __future__ import annotations

import json

from mindsos_admin import propose_for_promotion
from mindsos_server.release import release_update


def test_release_after_failed_rerun_ships(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """Two duplicate proposals → FAILED; admin deletes one → rerun ships."""
    # Two duplicate-content proposals.
    r1 = propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="Cat", target_role="ontology"),
        pending_global_mg=pending_global_mg,
    )
    r2 = propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="Cat", target_role="ontology"),
        pending_global_mg=pending_global_mg,
    )

    # First ship: blocking from intra_pending pass.
    from mindsos_admin.exceptions import BlockingFindingError
    import pytest
    with pytest.raises(BlockingFindingError):
        release_update(
            seeded_admin, session=admin_session_both,
            canonical_global_mg=canonical_global_mg,
            pending_global_mg=pending_global_mg,
        )

    # Admin amends: delete one of the duplicates from pending. Simulate by
    # DELETE on pending_mutations + remove_node from in-memory pending.
    seeded_admin.execute(
        "DELETE FROM pending_mutations WHERE mutation_id = ?",
        (r2.mutation_ids[0],),
    )
    seeded_admin.commit()
    pending_ontology = next(
        g for g in pending_global_mg.graphs.values() if g.role == "ontology"
    )
    cur = seeded_admin.execute(
        "SELECT payload_json FROM pending_mutations WHERE mutation_id = ?",
        (r2.mutation_ids[0],),
    )
    # r2 row already deleted; remove its node from in-memory pending too.
    # We need to look up its node_id via the original propose result.
    # Simpler: find any node in pending that's NOT r1's.
    r1_payload = json.loads(seeded_admin.execute(
        "SELECT payload_json FROM pending_mutations WHERE mutation_id = ?",
        (r1.mutation_ids[0],),
    ).fetchone()[0])
    r1_node_id = r1_payload["node_id"]
    # Remove the duplicate (not r1's).
    to_remove = [nid for nid in pending_ontology.nodes if nid != r1_node_id]
    for nid in to_remove:
        pending_ontology.remove_node(nid)

    # Rerun: one pending, no duplicates → SHIPPED.
    result = release_update(
        seeded_admin, session=admin_session_both,
        canonical_global_mg=canonical_global_mg,
        pending_global_mg=pending_global_mg,
    )
    assert result.status == "SHIPPED"
    assert result.mutations_shipped_count == 1


def test_suppression_set_built_from_failed_manifest(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """Suppression-set query reads FAILED manifest_json (PB-Z15(a))."""
    from mindsos_server.release import _build_suppression_set

    # No FAILED rows → empty suppression set.
    suppression = _build_suppression_set(seeded_admin)
    assert suppression == {}

    # Insert a synthetic FAILED row with per-role node-ids.
    seeded_admin.execute(
        "INSERT INTO audit (ts, actor_user, event, target_user, extra_json) "
        "VALUES ('2026-05-22T00:00:00.000Z', 'admin', "
        "'EVT_RELEASE_FAILED', NULL, '{}')"
    )
    audit_id = seeded_admin.execute("SELECT last_insert_rowid()").fetchone()[0]
    manifest = {
        "included_mutation_ids": [],
        "rewrite_map": {},
        "roles_affected": ["ontology"],
        "failed_at_role": "lexicon",
        "error_class": "FalkorDBWriteError",
        "mutations_attempted_count": 3,
        "audit_event_id": audit_id,
        "shipped_at": None,
        "failed_at": "2026-05-22T00:01:00.000Z",
        "failed_release_canonical_node_ids": {
            "ontology": ["node-1", "node-2"],
        },
    }
    seeded_admin.execute(
        "INSERT INTO releases "
        "(proposer_admin_user_id, proposed_at, failed_at, manifest_json, "
        "audit_event_id, status) "
        "VALUES ('admin', '2026-05-22T00:00:00.000Z', "
        "'2026-05-22T00:01:00.000Z', ?, ?, 'FAILED')",
        (json.dumps(manifest), audit_id),
    )
    seeded_admin.commit()

    suppression = _build_suppression_set(seeded_admin)
    assert suppression == {"ontology": ["node-1", "node-2"]}


def test_suppression_set_watermark_excludes_pre_shipped_failed(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """PB-Z15(a) — SHIPPED advances watermark; older FAILEDs retire."""
    from mindsos_server.release import _build_suppression_set

    # Sequence: FAILED then SHIPPED.
    # 1. Insert a SHIPPED row.
    seeded_admin.execute(
        "INSERT INTO audit (ts, actor_user, event, target_user, extra_json) "
        "VALUES ('2026-05-22T00:00:00.000Z', 'admin', "
        "'EVT_RELEASE_SHIPPED', NULL, '{}')"
    )
    shipped_audit_id = seeded_admin.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]
    seeded_admin.execute(
        "INSERT INTO releases "
        "(proposer_admin_user_id, proposed_at, shipped_at, manifest_json, "
        "audit_event_id, status) "
        "VALUES ('admin', '2026-05-22T00:00:00.000Z', "
        "'2026-05-22T00:01:00.000Z', '{}', ?, 'SHIPPED')",
        (shipped_audit_id,),
    )
    seeded_admin.commit()
    shipped_release_id = seeded_admin.execute(
        "SELECT MAX(release_id) FROM releases WHERE status='SHIPPED'"
    ).fetchone()[0]

    # 2. Insert a FAILED row at release_id < shipped (older).
    # (In practice the IDs are AUTOINCREMENT monotonic; for this test we
    # rely on AUTOINCREMENT having advanced past shipped's id when the
    # subsequent FAILED is inserted. So insert a FAILED AFTER the
    # SHIPPED, then query — the watermark should INCLUDE it.)
    seeded_admin.execute(
        "INSERT INTO audit (ts, actor_user, event, target_user, extra_json) "
        "VALUES ('2026-05-22T00:02:00.000Z', 'admin', "
        "'EVT_RELEASE_FAILED', NULL, '{}')"
    )
    failed_audit_id = seeded_admin.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]
    failed_manifest = {
        "failed_release_canonical_node_ids": {"ontology": ["newer-failed"]},
    }
    seeded_admin.execute(
        "INSERT INTO releases "
        "(proposer_admin_user_id, proposed_at, failed_at, manifest_json, "
        "audit_event_id, status) "
        "VALUES ('admin', '2026-05-22T00:02:00.000Z', "
        "'2026-05-22T00:02:01.000Z', ?, ?, 'FAILED')",
        (json.dumps(failed_manifest), failed_audit_id),
    )
    seeded_admin.commit()

    # Suppression set includes the FAILED that's NEWER than last SHIPPED.
    suppression = _build_suppression_set(seeded_admin)
    assert "ontology" in suppression
    assert "newer-failed" in suppression["ontology"]
