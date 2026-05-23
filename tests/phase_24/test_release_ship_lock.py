"""RELEASE_SHIP_LOCK serializes concurrent release_update calls.

Per ADR-0006 §am1 + PB-12(a) — threading.RLock substrate.
"""

from __future__ import annotations

import threading
import time

from mindsos_admin import propose_for_promotion
from mindsos_server.locks import RELEASE_SHIP_LOCK
from mindsos_server.release import release_update


def test_release_ship_lock_is_threading_rlock():
    """ADR-0006 §am1 — substrate is threading.RLock."""
    # Reentrant lock supports the same thread acquiring twice without deadlock.
    assert RELEASE_SHIP_LOCK.acquire(timeout=1)
    assert RELEASE_SHIP_LOCK.acquire(timeout=1)
    RELEASE_SHIP_LOCK.release()
    RELEASE_SHIP_LOCK.release()


def test_release_ship_lock_serializes_concurrent_ship(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """Two concurrent release_update calls serialize on RELEASE_SHIP_LOCK.

    Phase 24 v1 is single-process; this test asserts the threading
    primitive serializes correctly. The release_update body operates
    on shared in-memory metagraphs; without the lock, two threads
    racing on the same canonical_global_mg would conflict.
    """
    # Setup: one pending mutation.
    propose_for_promotion(
        seeded_admin, session=admin_session_both,
        proposal=atom_proposal_factory(value="OnlyOne"),
        pending_global_mg=pending_global_mg,
    )

    # Acquire the lock in main thread; attempt non-blocking acquire from
    # another thread; should fail.
    RELEASE_SHIP_LOCK.acquire()
    try:
        result_holder = []

        def try_acquire():
            got = RELEASE_SHIP_LOCK.acquire(blocking=False)
            result_holder.append(got)
            if got:
                RELEASE_SHIP_LOCK.release()

        t = threading.Thread(target=try_acquire)
        t.start()
        t.join(timeout=2)
        # Other thread should NOT have acquired (lock held by main).
        assert result_holder == [False]
    finally:
        RELEASE_SHIP_LOCK.release()
