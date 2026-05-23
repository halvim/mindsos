"""
PB-39 — hard_delete_user calls ``persister.delete(target_user_id)``
and denormalizes the return into both audit + return value.
"""

from __future__ import annotations

from mindsos_core import Metagraph

from mindsos_server.admin import hard_delete_user
from mindsos_server.session import Session


def test_local_dump_existed_true_when_persister_had_dump(
    seeded_admin, fast_params, persister,
) -> None:
    from mindsos_server.users import insert_user
    insert_user(
        seeded_admin, "alice", "pw",
        actor_role="user", params=fast_params,
    )
    seeded_admin.commit()

    # Pre-populate the persister so delete() returns True.
    persister.save("alice", Metagraph(name="local_knowledge:alice"))

    admin_session = Session.for_testing("admin-caller", is_admin=True)
    result = hard_delete_user(
        seeded_admin, admin_session,
        target_user_id="alice",
        persister=persister,
    )
    assert result.local_dump_existed is True
    # Persister is now empty.
    assert persister.load("alice") is None


def test_local_dump_existed_false_when_persister_empty(
    seeded_admin, fast_params, persister,
) -> None:
    from mindsos_server.users import insert_user
    insert_user(
        seeded_admin, "alice", "pw",
        actor_role="user", params=fast_params,
    )
    seeded_admin.commit()

    admin_session = Session.for_testing("admin-caller", is_admin=True)
    result = hard_delete_user(
        seeded_admin, admin_session,
        target_user_id="alice",
        persister=persister,
    )
    assert result.local_dump_existed is False


def test_persister_none_yields_local_dump_existed_false(
    seeded_admin, fast_params,
) -> None:
    """Backward-compat: caller can omit persister kwarg entirely."""
    from mindsos_server.users import insert_user
    insert_user(
        seeded_admin, "alice", "pw",
        actor_role="user", params=fast_params,
    )
    seeded_admin.commit()

    admin_session = Session.for_testing("admin-caller", is_admin=True)
    result = hard_delete_user(
        seeded_admin, admin_session,
        target_user_id="alice",
    )
    assert result.local_dump_existed is False
