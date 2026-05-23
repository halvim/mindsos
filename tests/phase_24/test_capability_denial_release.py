"""Capability denial — CAN_APPROVE_RELEASE required for release_update."""

from __future__ import annotations

import pytest

from mindsos_server.audit import EVT_PERMISSION_DENIED
from mindsos_server.errors import PermissionDeniedError
from mindsos_server.release import release_update


def test_non_admin_session_denied_for_release(
    seeded_admin, non_admin_session, canonical_global_mg, pending_global_mg,
):
    """USER_CAPS empty → PermissionDeniedError + EVT_PERMISSION_DENIED."""
    with pytest.raises(PermissionDeniedError):
        release_update(
            seeded_admin,
            session=non_admin_session,
            canonical_global_mg=canonical_global_mg,
            pending_global_mg=pending_global_mg,
        )

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
    assert extra["capability"] == "CAN_APPROVE_RELEASE"
    assert extra["verb"] == "release_update"


def test_propose_cap_alone_insufficient_for_release(
    seeded_admin, admin_session_propose,
    canonical_global_mg, pending_global_mg,
):
    """CAN_PROPOSE_MUTATION ≠ CAN_APPROVE_RELEASE (separate caps)."""
    with pytest.raises(PermissionDeniedError):
        release_update(
            seeded_admin,
            session=admin_session_propose,
            canonical_global_mg=canonical_global_mg,
            pending_global_mg=pending_global_mg,
        )
