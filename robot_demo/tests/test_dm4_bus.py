"""DM-4 — BrainBus isolation tests (no domain stack; 3.10 sandbox).

Covers the PB-FFF design: pub/sub fan-out, direct send, blocking
request→reply resolving a Future on the source's consumer thread, the
deferred-reply pattern (DEFER + a later completion callback), the bounded
timeout path, and remote-handler-exception propagation.
"""

from __future__ import annotations

import threading
import time

import pytest

from robot_demo.backend.bus import (
    DEFER,
    BrainBus,
    BusError,
    BusTimeout,
    Message,
)


@pytest.fixture
def bus():
    b = BrainBus()
    for bid in ("mgr", "a1"):
        b.register_endpoint(bid)
    yield b
    b.stop()


def test_publish_fans_out_to_subscribers(bus):
    got = []
    ev = threading.Event()

    def on_caps(msg: Message):
        got.append((msg.src, msg.payload))
        ev.set()

    bus.subscribe("mgr", "capability-report", on_caps)
    bus.publish("a1", "capability-report", {"caps": ["move_to"]})

    assert ev.wait(2.0)
    assert got == [("a1", {"caps": ["move_to"]})]


def test_direct_send_fire_and_forget(bus):
    got = []
    ev = threading.Event()

    def on_note(msg: Message):
        got.append(msg.payload)
        ev.set()

    bus.set_handler("a1", "note", on_note)
    bus.send("mgr", "a1", "note", "hello")

    assert ev.wait(2.0)
    assert got == ["hello"]


def test_request_reply_roundtrip(bus):
    # a1 answers synchronously; mgr's request blocks then gets the reply
    def on_ping(msg: Message):
        return {"pong": msg.payload["n"] + 1}

    bus.set_handler("a1", "ping", on_ping)
    reply = bus.request("mgr", "a1", "ping", {"n": 41}, timeout=2.0)
    assert reply == {"pong": 42}


def test_deferred_reply_keeps_consumer_responsive(bus):
    # a1's handler defers (simulating il.enqueue) and replies from another
    # thread later — the dispatch→report shape DM-4 actually uses.
    def on_dispatch(msg: Message):
        def worker():
            time.sleep(0.05)
            bus.reply(msg, payload={"status": "succeeded", "did": msg.payload})
        threading.Thread(target=worker, daemon=True).start()
        return DEFER

    bus.set_handler("a1", "dispatch", on_dispatch)
    reply = bus.request("mgr", "a1", "dispatch", "move_to", timeout=2.0)
    assert reply == {"status": "succeeded", "did": "move_to"}


def test_request_times_out_when_no_reply(bus):
    bus.set_handler("a1", "blackhole", lambda msg: DEFER)  # never replies
    with pytest.raises(BusTimeout):
        bus.request("mgr", "a1", "blackhole", None, timeout=0.2)


def test_remote_handler_exception_propagates(bus):
    def boom(msg: Message):
        raise ValueError("nope")

    bus.set_handler("a1", "boom", boom)
    with pytest.raises(BusError):
        bus.request("mgr", "a1", "boom", None, timeout=2.0)


def test_unknown_kind_replies_error_not_hang(bus):
    with pytest.raises(BusError):
        bus.request("mgr", "a1", "no-such-kind", None, timeout=2.0)


def test_concurrent_requests_resolve_independently(bus):
    # two in-flight requests from mgr to a1; correlation ids keep them apart
    def on_echo(msg: Message):
        def worker():
            time.sleep(0.02)
            bus.reply(msg, payload=msg.payload)
        threading.Thread(target=worker, daemon=True).start()
        return DEFER

    bus.set_handler("a1", "echo", on_echo)
    results = {}

    def fire(n):
        results[n] = bus.request("mgr", "a1", "echo", n, timeout=2.0)

    threads = [threading.Thread(target=fire, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=3.0)
    assert results == {i: i for i in range(5)}
