"""
ADR-0008 refcount-install — nested in-process ``with`` invocations
bump refcount; teardown decrements; record cleared on refcount→0.

Exercises the bump branch that is unreachable in v1 production (single-
process CLI per-command-process model) but ships at v1 per ADR-0008
§Decision verbatim (PB-29).
"""

from __future__ import annotations

from mindsos_server import orchestrator
from mindsos_server.orchestrator import read_other_local


def test_nested_with_bumps_refcount_to_2_then_back_to_0(
    seeded_user, admin_session, persister, kl,
) -> None:
    # Outer entry: install, refcount=1, record exists.
    with read_other_local(
        seeded_user, admin_session, "alice",
        persister=persister, kl=kl,
    ) as mg_outer:
        rec = orchestrator._installed_locals["alice"]
        assert rec.refcount == 1
        assert rec.transient is True

        # Inner entry: bump refcount to 2; same Metagraph reused.
        with read_other_local(
            seeded_user, admin_session, "alice",
            persister=persister, kl=kl,
        ) as mg_inner:
            rec_after_bump = orchestrator._installed_locals["alice"]
            assert rec_after_bump.refcount == 2
            assert mg_inner is mg_outer

        # Inner exit: refcount back to 1, record still present.
        rec_after_inner_exit = orchestrator._installed_locals["alice"]
        assert rec_after_inner_exit.refcount == 1

    # Outer exit: refcount→0, record cleared.
    assert "alice" not in orchestrator._installed_locals


def test_install_was_existing_true_on_bump_branch(
    seeded_user, admin_session, persister, kl,
) -> None:
    """The 2nd entry's audit row carries install_was_existing=True."""
    with read_other_local(
        seeded_user, admin_session, "alice",
        persister=persister, kl=kl,
    ):
        with read_other_local(
            seeded_user, admin_session, "alice",
            persister=persister, kl=kl,
        ):
            # Inner audit row already written.
            rows = seeded_user.execute(
                """
                SELECT extra_json FROM audit
                 WHERE event = 'EVT_CROSS_USER_READ_INSTALL'
                   AND target_user = 'alice'
              ORDER BY id ASC
                """,
            ).fetchall()
            assert len(rows) == 2
            # First row: was_existing=False; Second row: was_existing=True.
            import json
            first = json.loads(rows[0][0])
            second = json.loads(rows[1][0])
            assert first["install_was_existing"] is False
            assert first["refcount_after_acquire"] == 1
            assert second["install_was_existing"] is True
            assert second["refcount_after_acquire"] == 2
