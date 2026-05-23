"""Capability denial — CAN_PROPOSE_MUTATION required for propose_for_promotion.

Per ADR-0002 §am2 + Phase 21 _require_or_audit pattern.
"""

from __future__ import annotations

import pytest

from mindsos_admin import propose_for_promotion
from mindsos_server.audit import EVT_PERMISSION_DENIED
from mindsos_server.errors import PermissionDeniedError


def test_non_admin_session_denied(
    seeded_admin, non_admin_session,
    pending_global_mg, atom_proposal_factory,
):
    """USER_CAPS empty → PermissionDeniedError + EVT_PERMISSION_DENIED."""
    proposal = atom_proposal_factory()
    with pytest.raises(PermissionDeniedError):
        propose_for_promotion(
            seeded_admin,
            session=non_admin_session,
            proposal=proposal,
            pending_global_mg=pending_global_mg,
        )

    # EVT_PERMISSION_DENIED audit row emitted (committed).
    cur = seeded_admin.execute(
        "SELECT actor_user, event, extra_json FROM audit "
        "WHERE event = ?",
        (EVT_PERMISSION_DENIED,),
    )
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "alice-caller"
    import json
    extra = json.loads(row[2])
    assert extra["capability"] == "CAN_PROPOSE_MUTATION"
    assert extra["verb"] == "propose_for_promotion"


def test_admin_with_only_propose_cap_allowed(
    seeded_admin, admin_session_propose,
    pending_global_mg, atom_proposal_factory,
):
    """Session with CAN_PROPOSE_MUTATION (only) succeeds."""
    proposal = atom_proposal_factory()
    result = propose_for_promotion(
        seeded_admin, session=admin_session_propose,
        proposal=proposal, pending_global_mg=pending_global_mg,
    )
    assert len(result.mutation_ids) == 1
