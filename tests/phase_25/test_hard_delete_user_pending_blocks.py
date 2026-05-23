"""
PB-30 + ADR-0114 §am4 — hard_delete_user with pending promotion
mutations blocks with :class:`UserHasPromotionHistoryError`.
"""

from __future__ import annotations

import pytest

from mindsos_server.admin import hard_delete_user
from mindsos_server.errors import UserHasPromotionHistoryError
from mindsos_server.session import Session


def _seed_pending_mutation_for(conn, user_id: str) -> int:
    """Insert a minimal pending_mutations row keyed on user_id."""
    audit_cur = conn.execute(
        "INSERT INTO audit (ts, actor_user, event, target_user, extra_json) "
        "VALUES ('2026-05-23T00:00:00Z', ?, 'EVT_PROMOTION_PROPOSED', ?, '{}')",
        (user_id, user_id),
    )
    audit_id = audit_cur.lastrowid
    cur = conn.execute(
        """
        INSERT INTO pending_mutations
            (proposer_admin_user_id, source_user_id, proposed_at,
             mutation_type, payload_json, audit_event_id,
             frozen_user_local_node_id, shipped_in_release)
        VALUES (?, NULL, '2026-05-23T00:00:00Z', 'PROMOTION',
                '{}', ?, NULL, NULL)
        """,
        (user_id, audit_id),
    )
    conn.commit()
    return cur.lastrowid


def test_hard_delete_with_pending_mutation_raises(
    seeded_admin, fast_params, persister,
) -> None:
    # Seed a second admin (target) — sole-admin invariant doesn't fire.
    from mindsos_server.users import insert_user
    insert_user(
        seeded_admin, "admin2", "pw",
        actor_role="admin", params=fast_params,
    )
    seeded_admin.commit()

    _seed_pending_mutation_for(seeded_admin, "admin2")

    admin_session = Session.for_testing("admin-caller", is_admin=True)
    with pytest.raises(UserHasPromotionHistoryError) as exc_info:
        hard_delete_user(
            seeded_admin, admin_session,
            target_user_id="admin2",
            persister=persister,
        )
    assert exc_info.value.user_id == "admin2"
    assert len(exc_info.value.pending_ids) == 1
    assert exc_info.value.release_ids == []


def test_user_row_survives_blocked_hard_delete(
    seeded_admin, fast_params, persister,
) -> None:
    from mindsos_server.users import insert_user
    insert_user(
        seeded_admin, "admin2", "pw",
        actor_role="admin", params=fast_params,
    )
    seeded_admin.commit()
    _seed_pending_mutation_for(seeded_admin, "admin2")

    admin_session = Session.for_testing("admin-caller", is_admin=True)
    with pytest.raises(UserHasPromotionHistoryError):
        hard_delete_user(
            seeded_admin, admin_session,
            target_user_id="admin2",
            persister=persister,
        )

    row = seeded_admin.execute(
        "SELECT user_id FROM users WHERE user_id = 'admin2'",
    ).fetchone()
    assert row is not None  # admin_tx rolled back the (non-)delete.
