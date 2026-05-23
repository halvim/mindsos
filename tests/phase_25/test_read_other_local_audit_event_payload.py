"""
PB-31 — :data:`EVT_CROSS_USER_READ_INSTALL` audit payload shape lock.

Asserts the full key roster + value types at v1.
"""

from __future__ import annotations

import json

from mindsos_server.orchestrator import read_other_local


def test_audit_row_has_full_payload_shape(
    seeded_user, admin_session, persister, kl,
) -> None:
    with read_other_local(
        seeded_user, admin_session, "alice",
        persister=persister, kl=kl,
    ):
        pass

    row = seeded_user.execute(
        """
        SELECT actor_user, event, target_user, extra_json
          FROM audit
         WHERE event = 'EVT_CROSS_USER_READ_INSTALL'
        """,
    ).fetchone()
    assert row is not None
    actor_user, event, target_user, extra_json = row
    assert actor_user == "admin-caller"
    assert event == "EVT_CROSS_USER_READ_INSTALL"
    assert target_user == "alice"

    extra = json.loads(extra_json)
    assert set(extra.keys()) == {
        "admin_user_id",
        "target_user_id",
        "transient",
        "install_was_existing",
        "refcount_after_acquire",
        "target_role_graph_node_counts",
    }
    assert extra["admin_user_id"] == "admin-caller"
    assert extra["target_user_id"] == "alice"
    assert extra["transient"] is True
    assert extra["install_was_existing"] is False
    assert extra["refcount_after_acquire"] == 1
    # On cold install, KL auto-ensures memories + capacity-state with 0 nodes.
    counts = extra["target_role_graph_node_counts"]
    assert isinstance(counts, dict)
    assert counts.get("memories") == 0
    assert counts.get("capacity-state") == 0


def test_audit_row_committed_after_ctx_mgr_entry(
    seeded_user, admin_session, persister, kl,
) -> None:
    """PB-R7-02 — commit happens inside ctx mgr; row visible mid-yield."""
    with read_other_local(
        seeded_user, admin_session, "alice",
        persister=persister, kl=kl,
    ):
        # Inside yield body, BEFORE caller commits. The orchestrator
        # has already committed via PB-R7-02.
        row = seeded_user.execute(
            "SELECT COUNT(*) FROM audit "
            "WHERE event = 'EVT_CROSS_USER_READ_INSTALL'",
        ).fetchone()
        assert row[0] == 1
