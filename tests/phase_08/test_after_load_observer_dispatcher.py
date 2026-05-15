"""RR-9 A — _dispatch_after_load per-observer exception isolation."""

from __future__ import annotations

import logging
from typing import List

from mindsos_core._observers import AfterLoadCallback, _dispatch_after_load


def test_dispatch_after_load_invokes_all_callbacks_in_order() -> None:
    """Single fire — every callback receives the metagraph in registration order."""
    fired: List[int] = []
    sentinel = object()

    def cb1(mg: object) -> None:
        fired.append(1)

    def cb2(mg: object) -> None:
        fired.append(2)

    def cb3(mg: object) -> None:
        fired.append(3)

    _dispatch_after_load([cb1, cb2, cb3], sentinel)
    assert fired == [1, 2, 3]


def test_dispatch_after_load_isolates_failing_observer_per_rr_9_a(
    caplog,
) -> None:
    """RR-9 A — failing observer is logged + swallowed; subsequent fire."""
    fired: List[int] = []
    sentinel = object()

    def cb_good_1(mg: object) -> None:
        fired.append(1)

    def cb_raises(mg: object) -> None:
        raise RuntimeError("simulated InstanceLoader failure")

    def cb_good_2(mg: object) -> None:
        fired.append(2)

    callbacks: List[AfterLoadCallback] = [cb_good_1, cb_raises, cb_good_2]

    caplog.set_level(logging.WARNING, logger="mindsos_core._observers")
    _dispatch_after_load(callbacks, sentinel)

    # RR-9 A — failing observer doesn't block the chain.
    assert fired == [1, 2]
    # Failing observer logged at WARNING level.
    assert any(
        "swallowing per Phase 08 RR-9 A" in rec.message
        for rec in caplog.records
    )


def test_dispatch_after_load_empty_observer_list() -> None:
    """Empty observer list — no-op."""
    sentinel = object()
    _dispatch_after_load([], sentinel)


def test_dispatch_after_load_keyword_only_does_not_swallow_keyboard_interrupt() -> None:
    """RR-9 A swallows ``Exception``; KeyboardInterrupt + SystemExit must propagate.

    Standard library convention: bare ``except Exception`` does not
    catch ``BaseException`` subclasses (KeyboardInterrupt / SystemExit).
    Verify the implementation honors this.
    """
    import pytest

    sentinel = object()

    def cb_kb_interrupt(mg: object) -> None:
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        _dispatch_after_load([cb_kb_interrupt], sentinel)
