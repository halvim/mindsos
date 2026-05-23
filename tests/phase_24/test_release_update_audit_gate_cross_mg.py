"""Audit gate cross-mg finding — pending vs canonical collision.

Per Phase 16 PB-K2 + ADR-0144 §am2 + PB-24(b) two-pass.
"""

from __future__ import annotations

import pytest

from mindsos_admin import propose_for_promotion
from mindsos_admin.exceptions import BlockingFindingError
from mindsos_server.release import release_update


def test_cross_mg_blocking_against_canonical(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """Propose+ship; propose-near-duplicate; ship → cross-mg blocking."""
    # Ship first: "Apple" lands in canonical.
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="Apple", target_role="ontology"),
        pending_global_mg=pending_global_mg,
    )
    r1 = release_update(
        seeded_admin, session=admin_session_both,
        canonical_global_mg=canonical_global_mg,
        pending_global_mg=pending_global_mg,
    )
    assert r1.status == "SHIPPED"

    # Propose another "Apple" — different node_id, identical IRI tail content.
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="Apple", target_role="ontology"),
        pending_global_mg=pending_global_mg,
    )

    # Second ship: cross-mg pass finds Apple-in-canonical ~ Apple-in-pending.
    # Per Phase 16 cross-mg form, no self-exclusion → blocking finding.
    with pytest.raises(BlockingFindingError):
        release_update(
            seeded_admin, session=admin_session_both,
            canonical_global_mg=canonical_global_mg,
            pending_global_mg=pending_global_mg,
        )
