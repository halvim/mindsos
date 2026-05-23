"""
PB-30 + ADR-0114 §am4 — hard_delete_user with shipped releases blocks
with :class:`UserHasPromotionHistoryError`.
"""

from __future__ import annotations

import pytest

from mindsos_server.admin import hard_delete_user
from mindsos_server.errors import UserHasPromotionHistoryError
from mindsos_server.session import Session


def _seed_release_for(conn, user_id: str) -> int:
    """Insert a minimal releases row keyed on user_id."""
    audit_cur = conn.execute(
        "INSERT INTO audit (ts, actor_user, event, target_user, extra_json) "
        "VALUES ('2026-05-23T00:00:00Z', ?, 'EVT_RELEASE_SHIPPED', ?, '{}')",
        (user_id, user_id),
    )
    audit_id = audit_cur.lastrowid
    cur = conn.execute(
        """
        INSERT INTO releases
            (parent_release_id, proposer_admin_user_id,
             approver_admin_user_ids_json, proposed_at, shipped_at,
             failed_at, manifest_json, audit_event_id, status)
        VALUES (NULL, ?, NULL, '2026-05-23T00:00:00Z',
                '2026-05-23T00:00:00Z', NULL, '{}', ?, 'SHIPPED')
        """,
        (user_id, audit_id),
    )
    conn.commit()
    return cur.lastrowid


def test_hard_delete_with_release_history_raises(
    seeded_admin, fast_params, persister,
) -> None:
    from mindsos_server.users import insert_user
    insert_user(
        seeded_admin, "admin2", "pw",
        actor_role="admin", params=fast_params,
    )
    seeded_admin.commit()
    _seed_release_for(seeded_admin, "admin2")

    admin_session = Session.for_testing("admin-caller", is_admin=True)
    with pytest.raises(UserHasPromotionHistoryError) as exc_info:
        hard_delete_user(
            seeded_admin, admin_session,
            target_user_id="admin2",
            persister=persister,
        )
    assert exc_info.value.user_id == "admin2"
    assert exc_info.value.pending_ids == []
    assert len(exc_info.value.release_ids) == 1


def test_clean_admin_with_no_history_succeeds(
    seeded_admin, fast_params, persister,
) -> None:
    """Sanity: admin with NO promotion history hard-deletes cleanly."""
    from mindsos_server.users import insert_user
    insert_user(
        seeded_admin, "admin2", "pw",
        actor_role="admin", params=fast_params,
    )
    seeded_admin.commit()

    admin_session = Session.for_testing("admin-caller", is_admin=True)
    result = hard_delete_user(
        seeded_admin, admin_session,
        target_user_id="admin2",
        persister=persister,
    )
    assert result.target_user_id == "admin2"
    assert result.local_dump_existed is False
