"""Audit gate cross-mg finding — pending vs canonical collision.

Per Phase 16 PB-K2 + ADR-0144 §am2 + PB-24(b) two-pass.

Phase 16 ``_score_levenshtein`` operates on ``node_id`` strings; this
test pre-seeds canonical with a node having a near-identical node_id
as the pending candidate so cross-mg Lev fires blocking.
"""

from __future__ import annotations

import pytest

from mindsos_admin.exceptions import BlockingFindingError
from mindsos_server.release import release_update


def test_cross_mg_blocking_against_canonical(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg,
    inject_pending_node, inject_canonical_node,
):
    """Pending node near-identical to a node already in canonical → blocking."""
    # Pre-seed canonical with a node carrying a known controlled id.
    inject_canonical_node(
        canonical_global_mg=canonical_global_mg,
        node_id="apple-shipped-aaaaa-0001",
        value="Apple",
        target_role="ontology",
    )
    # Now propose a new pending node with a near-identical node_id.
    inject_pending_node(
        pending_global_mg=pending_global_mg,
        node_id="apple-shipped-aaaaa-0002",
        value="Apple",
        target_role="ontology",
    )

    # Cross-mg pass: Lev("...-0001", "...-0002") ~ 0.96 → blocking.
    with pytest.raises(BlockingFindingError):
        release_update(
            seeded_admin, session=admin_session_both,
            canonical_global_mg=canonical_global_mg,
            pending_global_mg=pending_global_mg,
        )
