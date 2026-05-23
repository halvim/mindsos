"""
ADR-0008 I-S3 — admin cross-user reads never flush.

The load-bearing test for the no-flush-on-teardown invariant.
``fail_save_for`` is set for the target user; if ``_release`` were to
call ``persister.save`` on transient teardown, the test would raise
:class:`FlushFailedError`. The test asserts that the ctx mgr exits
cleanly without any save attempt.
"""

from __future__ import annotations

from mindsos_server.orchestrator import read_other_local


def test_transient_install_never_flushes_on_teardown_is3(
    seeded_user, admin_session, persister, kl,
) -> None:
    # Arm the fault-injection: ANY save call for 'alice' would raise.
    persister.fail_save_for.add("alice")

    with read_other_local(
        seeded_user, admin_session, "alice",
        persister=persister, kl=kl,
    ) as mg:
        # Yield body runs without error — no save happens during install.
        assert mg is not None

    # If _release tried to save, FlushFailedError would have bubbled.
    # Reaching here proves I-S3 (admin reads never flush) holds.
