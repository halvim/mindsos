"""feat/subminds Slice 2 — ResourceLedger (resources.py).

acquire/release/holder_of/contention + the on_release resume hook.
"""

from __future__ import annotations

from mindsos_intelligence.resources import Contention, ResourceLedger


def test_acquire_records_holder_and_contention():
    led = ResourceLedger()
    led.acquire("t1", frozenset({"arm", "grip"}), tier=1, score=5)
    assert led.holder_of("arm").request_id == "t1"
    c = led.contention(frozenset({"grip"}))
    assert not c.free and c.conflicts[0].request_id == "t1"
    # disjoint resource is free
    assert led.contention(frozenset({"wheels"})).free


def test_empty_set_is_free_and_noop():
    led = ResourceLedger()
    assert led.acquire("t1", frozenset(), tier=0, score=0) is None
    assert led.contention(frozenset()) == Contention(free=True)


def test_release_frees_and_fires_hook():
    led = ResourceLedger()
    fired = []
    led.set_on_release(lambda freed, request_id: fired.append((frozenset(freed), request_id)))
    led.acquire("t1", frozenset({"arm"}), tier=1, score=5)
    freed = led.release("t1")
    assert freed == frozenset({"arm"})
    assert led.holder_of("arm") is None
    assert fired == [(frozenset({"arm"}), "t1")]


def test_contention_dedups_one_holder_over_many_resources():
    led = ResourceLedger()
    led.acquire("t1", frozenset({"a", "b"}), tier=1, score=5)
    c = led.contention(frozenset({"a", "b"}))
    assert len(c.conflicts) == 1  # one hold, not two


def test_release_unknown_task_is_noop():
    led = ResourceLedger()
    assert led.release("nope") == frozenset()
