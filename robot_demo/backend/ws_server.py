"""DM-4 Seam A — the brains WebSocket server (plan §2.2, WS contract).

A pure-asyncio ``websockets`` server (the page is served separately, per
``demo_ui/HOW_TO_USE.md`` — so no HTTP/ASGI surface is needed here; fastapi/
uvicorn stay available for the DM-8 graph-query endpoint). It is the SERVER→
BROWSER side of ``ROBOT_DEMO_WS_CONTRACT.md`` and the real-backend replacement
for ``demo_ui/mock_ws_server.js``.

Lifecycle per the contract: on connect → send ``hello`` (+ a ``server_status``
snapshot if a provider is wired); then stream ``state`` / ``message`` / ``pose``
/ ``reset`` / ``server_status`` frames drained from the
:class:`~robot_demo.backend.frames.FrameHub`; accept ``command`` frames and
route them to an injected handler.

**Threading (PB-ZZ / PB-FFF).** The server owns its OWN event loop in its own
daemon thread; the brains (IL pools), the bus (consumer threads) and the sim
(clock thread) all publish frames via ``hub.publish`` from their threads, and
the hub marshals them onto this loop. Inbound commands run on the loop thread
and only ever *submit* to a brain's IL pool (non-blocking).

**Targeted replies (DM-4 L5, design-log PB-16).** Most frames are broadcast via
the hub, but ``state_snapshot`` (an export reply) and the future
``import_result`` must reach only the requesting client. The command handler is
given a per-connection ``respond(frame)`` that is **thread-safe** (it marshals
onto the loop), so an off-loop export worker (PB-8) can reply when its
serialize completes.

**Server panel (DM-4).** A ``status_provider`` callable (``() -> dict`` server
status frame, already sanitized) is sent once on connect and broadcast by an
on-loop heartbeat (~3s) — no extra thread (PB-20: it stops with the loop).
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, Callable, Dict, Optional

import websockets

from .frames import DemoEvents, FrameHub

#: command handler signature: ``on_command(name, args, respond=None)``.
#: ``respond(frame)`` sends a frame to the requesting client only (thread-safe).
CommandHandler = Callable[..., None]

#: ``() -> dict`` returning a fully-shaped, sanitized ``server_status`` frame.
StatusProvider = Callable[[], dict]


class DemoWSServer:
    """Serves the brains socket; bridges FrameHub → clients, commands → handler."""

    def __init__(
        self,
        hub: FrameHub,
        on_command: CommandHandler,
        *,
        beats_total: int = 7,
        status_provider: Optional[StatusProvider] = None,
        heartbeat_s: float = 3.0,
    ) -> None:
        self._hub = hub
        self._on_command = on_command
        self._beats_total = beats_total
        self._status_provider = status_provider
        self._heartbeat_s = heartbeat_s
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._ready = threading.Event()

    # ── per-connection ────────────────────────────────────────────────
    async def _handler(self, ws) -> None:
        await ws.send(json.dumps(DemoEvents.hello_frame(self._beats_total)))
        if self._status_provider is not None:
            try:
                await ws.send(json.dumps(self._status_provider()))
            except Exception as exc:  # never let a bad status kill the connect
                print(f"[ws] status_provider error on connect: {exc}")
        q = self._hub.register()
        respond = self._make_respond(q)
        pump = asyncio.create_task(self._pump(ws, q))
        try:
            async for raw in ws:
                self._on_inbound(raw, respond)
        except websockets.ConnectionClosed:
            pass
        finally:
            self._hub.unregister(q)
            pump.cancel()

    async def _pump(self, ws, q: "asyncio.Queue[dict]") -> None:
        """Drain this client's queue → socket. One task per connection."""
        try:
            while True:
                frame = await q.get()
                await ws.send(json.dumps(frame))
        except (websockets.ConnectionClosed, asyncio.CancelledError):
            pass

    def _make_respond(self, q: "asyncio.Queue[dict]") -> Callable[[dict], None]:
        """A thread-safe per-connection responder: an off-loop worker can call
        it; it marshals the put onto the loop (asyncio.Queue is not
        thread-safe)."""
        loop = self._loop

        def respond(frame: dict) -> None:
            if loop is None or loop.is_closed():
                return

            def _put() -> None:
                try:
                    q.put_nowait(frame)
                except asyncio.QueueFull:
                    pass

            loop.call_soon_threadsafe(_put)

        return respond

    def _on_inbound(self, raw, respond: Callable[[dict], None]) -> None:
        try:
            cmd = json.loads(raw)
        except (ValueError, TypeError):
            return
        if not isinstance(cmd, dict) or cmd.get("type") != "command":
            return
        name = cmd.get("name")
        args = cmd.get("args") or {}
        if not name:
            return
        try:
            self._on_command(name, args, respond)  # only SUBMITS (non-blocking)
        except Exception as exc:  # never let one command kill the reader
            print(f"[ws] command {name!r} handler error: {exc}")

    # ── server lifecycle (own loop thread) ────────────────────────────
    async def _heartbeat(self) -> None:
        """Broadcast a ``server_status`` frame every ``heartbeat_s`` (on-loop —
        no extra thread; cancelled when the loop stops)."""
        assert self._stop_event is not None
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(self._heartbeat_s)
                if self._status_provider is None:
                    continue
                try:
                    self._hub.publish(self._status_provider())
                except Exception as exc:
                    print(f"[ws] heartbeat status error: {exc}")
        except asyncio.CancelledError:
            pass

    async def _serve(self, host: str, port: int) -> None:
        self._stop_event = asyncio.Event()
        hb: Optional[asyncio.Task] = None
        if self._status_provider is not None:
            hb = asyncio.create_task(self._heartbeat())
        async with websockets.serve(self._handler, host, port):
            self._ready.set()
            await self._stop_event.wait()
        if hb is not None:
            hb.cancel()

    def _run(self, host: str, port: int) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._hub.bind_loop(loop)          # frames can flow once bound
        try:
            loop.run_until_complete(self._serve(host, port))
        finally:
            loop.close()

    def start(self, host: str = "0.0.0.0", port: int = 8765,
              *, wait: float = 5.0) -> None:
        """Start the server in a daemon thread; block until it is listening."""
        self._thread = threading.Thread(
            target=self._run, args=(host, port), name="ws-server", daemon=True
        )
        self._thread.start()
        if not self._ready.wait(timeout=wait):
            raise RuntimeError("ws server did not become ready in time")

    def stop(self) -> None:
        if self._loop is not None and self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None


__all__ = ["DemoWSServer", "CommandHandler", "StatusProvider"]
