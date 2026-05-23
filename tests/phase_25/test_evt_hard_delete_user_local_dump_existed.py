"""
PB-39 + ADR-0013 §am — :data:`EVT_HARD_DELETE_USER`.extra_json gains
additive key ``local_dump_existed``.
"""

from __future__ import annotations

import json

from mindsos_core import Metagraph

from mindsos_server.admin import hard_delete_user
from mindsos_server.session import Session


def test_audit_extra_includes_local_dump_existed_true(
    seeded_admin, fast_params, persister,
) -> None:
    from mindsos_server.users import insert_user
    insert_user(
        seeded_admin, "alice", "pw",
        actor_role="user", params=fast_params,
    )
    seeded_admin.commit()
    persister.save("alice", Metagraph(name="local_knowledge:alice"))

    admin_session = Session.for_testing("admin-caller", is_admin=True)
    hard_delete_user(
        seeded_admin, admin_session,
        target_user_id="alice",
        persister=persister,
    )

    row = seeded_admin.execute(
        "SELECT extra_json FROM audit "
        "WHERE event = 'EVT_HARD_DELETE_USER' AND target_user = 'alice'",
    ).fetchone()
    assert row is not None
    extra = json.loads(row[0])
    assert extra["local_dump_existed"] is True
    assert set(extra.keys()) == {
        "prior_role", "was_disabled",
        "sessions_killed", "local_dump_existed",
    }


def test_audit_extra_includes_local_dump_existed_false(
    seeded_admin, fast_params, persister,
) -> None:
    from mindsos_server.users import insert_user
    insert_user(
        seeded_admin, "alice", "pw",
        actor_role="user", params=fast_params,
    )
    seeded_admin.commit()

    admin_session = Session.for_testing("admin-caller", is_admin=True)
    hard_delete_user(
        seeded_admin, admin_session,
        target_user_id="alice",
        persister=persister,
    )

    row = seeded_admin.execute(
        "SELECT extra_json FROM audit "
        "WHERE event = 'EVT_HARD_DELETE_USER' AND target_user = 'alice'",
    ).fetchone()
    extra = json.loads(row[0])
    assert extra["local_dump_existed"] is False
