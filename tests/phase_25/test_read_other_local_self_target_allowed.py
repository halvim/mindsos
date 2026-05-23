"""
PB-43 — self-target allowed in :func:`read_other_local`.

Admin reading their own Local is a degenerate but legal case;
saves callers a branch. The audit row is still emitted for symmetry.
"""

from __future__ import annotations

from mindsos_server.orchestrator import read_other_local


def test_admin_can_read_their_own_local(
    seeded_admin, admin_session, persister, kl,
) -> None:
    with read_other_local(
        seeded_admin, admin_session, "admin-caller",
        persister=persister, kl=kl,
    ) as mg:
        assert mg is not None

    row = seeded_admin.execute(
        "SELECT actor_user, target_user FROM audit "
        "WHERE event = 'EVT_CROSS_USER_READ_INSTALL'",
    ).fetchone()
    assert row == ("admin-caller", "admin-caller")
