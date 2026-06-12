"""DM-4 Seam B — the in-process BrainBus (plan §2.1, design-log PB-FFF).

All four brains share one process (P-1), so inter-brain comms is an
in-process bus: **one inbox ``queue.Queue`` per brain + a publish/subscribe
topic map**. The MindsOS-visible surface (the four ``comms.*`` capacities)
is built on top of this in :mod:`comms` — ``bus.py`` itself knows nothing
about L3/L4; if the topology ever splits into processes, only this file
changes (plan §2.1).

**PB-FFF — why a dedicated consumer thread per brain.** A Manager capacity
body that dispatches to an arm and then *awaits the report* blocks an IL
worker (``mgr max_workers=2``); the arm runs its lifecycle on its single
worker (``arm max_workers=1``). The report must therefore be routed back to
the Manager by something that is **not** an IL worker — otherwise the
single-worker arm + a re-entrant routing path deadlocks. So each endpoint
owns a **dedicated daemon consumer thread**: it drains the inbox, runs
handlers, and resolves the correlation ``Future`` the blocked requester
waits on. Routing never touches the IL worker pool.

**Request / reply.** ``request(src, dst, kind, payload, timeout)`` registers
a ``Future`` under a fresh ``corr_id``, sends the message, and blocks on
``future.result(timeout)`` (on the *caller's* thread — e.g. the Manager IL
worker). The destination's consumer thread runs the handler; the reply is
routed back to the caller's inbox, where the caller's consumer thread
resolves the ``Future`` by ``corr_id``. A handler that kicks off long async
work (e.g. ``arm.il.enqueue(run_lifecycle)``) returns :data:`DEFER` and
replies later via :meth:`BrainBus.reply` from a completion callback — so the
arm's consumer thread stays responsive during the lifecycle.

**Pub/sub.** ``publish(src, topic, payload)`` fans a message out to every
``subscribe(brain, topic, …)`` handler — the vehicle for the ``comms.
query_capabilities`` push-cache (PB-C): brains push their capability report
to a topic the Manager subscribes to; no synchronous cross-brain round-trip.

Pure stdlib, MuJoCo-free, no ``mindsos_*`` import — unit-testable in the
3.10 sandbox with no domain stack.
"""

from __future__ import annotations

import queue
import threading
import uuid
from concurrent.futures import Future
from concurrent.futures import TimeoutError as _FutureTimeout
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

#: A handler returns this to signal "I will reply later" (deferred reply,
#: via :meth:`BrainBus.reply`) — the consumer thread sends no auto-reply.
DEFER = object()


class BusTimeout(Exception):
    """A :meth:`BrainBus.request` did not receive a reply within the timeout."""


class BusError(Exception):
    """The remote handler raised; surfaced to the requester (honest dont-know)."""


@dataclass
class Message:
    """One bus message. ``corr_id`` is set for request/reply pairs only."""

    kind: str
    src: str
    dst: Optional[str] = None          # None for a topic publish
    topic: Optional[str] = None        # set for pub/sub
    corr_id: Optional[str] = None       # set for request/reply
    payload: Any = None
    is_reply: bool = False
    error: Optional[str] = None         # set on a reply when the handler raised


#: ``handler(message) -> reply_payload | DEFER | None``. For a request
#: (``corr_id`` set) a non-DEFER return is auto-replied; ``DEFER`` means the
#: handler will call :meth:`BrainBus.reply` itself. For send/publish the
#: return is ignored.
Handler = Callable[[Message], Any]


@dataclass
class _Endpoint:
    brain_id: str
    inbox: "queue.Queue[Optional[Message]]" = field(default_factory=queue.Queue)
    kind_handlers: Dict[str, Handler] = field(default_factory=dict)
    topic_handlers: Dict[str, List[Handler]] = field(default_factory=dict)
    thread: Optional[threading.Thread] = None


class BrainBus:
    """In-process message bus with per-brain inbox + dedicated consumer
    thread + correlation-Future request/reply (PB-FFF)."""

    def __init__(self) -> None:
        self._eps: Dict[str, _Endpoint] = {}
        self._pending: Dict[str, Future] = {}
        self._lock = threading.Lock()
        self._running = False

    # ── endpoint lifecycle ────────────────────────────────────────────
    def register_endpoint(self, brain_id: str) -> None:
        """Create the inbox + start the dedicated consumer thread for a brain.

        Idempotent: a second call for the same id is a no-op."""
        with self._lock:
            if brain_id in self._eps:
                return
            ep = _Endpoint(brain_id=brain_id)
            self._eps[brain_id] = ep
            self._running = True
            ep.thread = threading.Thread(
                target=self._consume, args=(ep,),
                name=f"bus-{brain_id}", daemon=True,
            )
            ep.thread.start()

    def stop(self) -> None:
        """Stop all consumer threads (pushes a sentinel to each inbox)."""
        self._running = False
        with self._lock:
            eps = list(self._eps.values())
        for ep in eps:
            ep.inbox.put(None)  # sentinel
        for ep in eps:
            if ep.thread is not None:
                ep.thread.join(timeout=2.0)
        # fail any still-pending requests so callers don't hang
        with self._lock:
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(BusError("bus stopped"))
            self._pending.clear()

    # ── handler registration ──────────────────────────────────────────
    def set_handler(self, brain_id: str, kind: str, handler: Handler) -> None:
        """Register the direct/request handler for a message ``kind``."""
        self._eps[brain_id].kind_handlers[kind] = handler

    def subscribe(self, brain_id: str, topic: str, handler: Handler) -> None:
        """Add a pub/sub handler for ``topic`` on this brain."""
        self._eps[brain_id].topic_handlers.setdefault(topic, []).append(handler)

    # ── sending ───────────────────────────────────────────────────────
    def send(self, src: str, dst: str, kind: str, payload: Any = None) -> None:
        """Fire-and-forget direct message (no reply expected)."""
        self._deliver(dst, Message(kind=kind, src=src, dst=dst, payload=payload))

    def publish(self, src: str, topic: str, payload: Any = None) -> None:
        """Fire-and-forget fan-out to every subscriber of ``topic``."""
        with self._lock:
            targets = [
                ep.brain_id for ep in self._eps.values() if topic in ep.topic_handlers
            ]
        for dst in targets:
            self._deliver(
                dst, Message(kind="__topic__", src=src, dst=dst,
                             topic=topic, payload=payload),
            )

    def request(
        self, src: str, dst: str, kind: str, payload: Any = None,
        *, timeout: float = 30.0,
    ) -> Any:
        """Blocking request → reply. Returns the reply payload.

        Blocks on the *caller's* thread; the reply is resolved by ``src``'s
        consumer thread (PB-FFF). Raises :class:`BusTimeout` on no reply,
        :class:`BusError` if the remote handler raised."""
        corr_id = uuid.uuid4().hex
        fut: Future = Future()
        with self._lock:
            self._pending[corr_id] = fut
        self._deliver(
            dst, Message(kind=kind, src=src, dst=dst, corr_id=corr_id,
                         payload=payload),
        )
        try:
            return fut.result(timeout=timeout)
        except _FutureTimeout:
            with self._lock:
                self._pending.pop(corr_id, None)
            raise BusTimeout(f"{src}->{dst} {kind!r} timed out after {timeout}s")

    def reply(self, message: Message, payload: Any = None,
              *, error: Optional[str] = None) -> None:
        """Send the reply for a request ``message`` back to its source.

        Used both by the auto-reply path and by deferred handlers (DEFER)."""
        if message.corr_id is None:
            return
        self._deliver(
            message.src,
            Message(kind=message.kind, src=message.dst or "", dst=message.src,
                    corr_id=message.corr_id, payload=payload, is_reply=True,
                    error=error),
        )

    # ── internals ─────────────────────────────────────────────────────
    def _deliver(self, dst: str, msg: Message) -> None:
        with self._lock:
            ep = self._eps.get(dst)
        if ep is not None:
            ep.inbox.put(msg)

    def _consume(self, ep: _Endpoint) -> None:
        while True:
            msg = ep.inbox.get()
            if msg is None:  # stop sentinel
                return
            try:
                if msg.is_reply:
                    self._resolve(msg)
                elif msg.topic is not None:
                    for h in ep.topic_handlers.get(msg.topic, []):
                        h(msg)
                else:
                    self._handle_direct(ep, msg)
            except Exception as exc:  # never let one message kill the thread
                if msg.corr_id is not None and not msg.is_reply:
                    self.reply(msg, error=f"{type(exc).__name__}: {exc}")

    def _handle_direct(self, ep: _Endpoint, msg: Message) -> None:
        handler = ep.kind_handlers.get(msg.kind)
        if handler is None:
            if msg.corr_id is not None:
                self.reply(msg, error=f"no handler for kind {msg.kind!r}")
            return
        result = handler(msg)
        if msg.corr_id is not None and result is not DEFER:
            self.reply(msg, payload=result)

    def _resolve(self, msg: Message) -> None:
        with self._lock:
            fut = self._pending.pop(msg.corr_id, None)
        if fut is None or fut.done():
            return
        if msg.error is not None:
            fut.set_exception(BusError(msg.error))
        else:
            fut.set_result(msg.payload)


__all__ = [
    "BrainBus",
    "Message",
    "Handler",
    "DEFER",
    "BusTimeout",
    "BusError",
]
