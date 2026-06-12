"""DM-4 Seam A — the brains WebSocket server (plan §2.2, WS contract).

A pure-asyncio ``websockets`` server (the page is served separately, per
``demo_ui/HOW_TO_USE.md`` — so no HTTP/ASGI surface is needed here; fastapi/
uvicorn stay available for the DM-8 graph-query endpoint). It is the SERVER→
BROWSER side of ``ROBOT_DEMO_WS_CONTRACT.md`` and the real-backend replacement
for ``demo_ui/mock_ws_server.js``.

Lifecycle per the contract: on connect → send ``hello``; then stream
``state`` / ``message`` / ``pose`` / ``reset`` frames drained from the
:class:`~robot_demo.backend.frames.FrameHub`; accept ``command`` frames and
route them to an injected handler (``place_order`` → a Manager
``run_lifecycle`` submission; ``play`` / ``pause`` / ``reset``).

**Threading (PB-ZZ / PB-FFF).** The server owns its OWN event loop in its own
daemon thread; the brains (IL pools), the bus (consumer threads) and the sim
(clock thread) all publish frames via ``hub.publish`` from their threads, and
the hub marshals them onto this loop. Inbound commands run on the loop thread
and only ever *submit* to a brain's IL pool (non-blocking) — the loop never
blocks on brain work.
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, Callable, Dict, Optional

import websockets

from .frames import DemoEvents, FrameHub

#: command handler signature: ``on_command(name: str, args: dict) -> None``.
CommandHandler = Callable[[str, Dict[str, Any]], None]


class DemoWSServer:
    """Serves the brains socket; bridges FrameHub → clients, commands → handler."""

    def __init__(
        self,
        hub: FrameHub,
        on_command: CommandHandler,
        *,
        beats_total: int = 7,
    ) -> None:
        self._hub = hub
        self._on_command = on_command
        self._beats_total = beats_total
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._ready = threading.Event()

    # ── per-connection ────────────────────────────────────────────────
    async def _handler(self, ws) -> None:
        await ws.send(json.dumps(DemoEvents.hello_frame(self._beats_total)))
        q = self._hub.register()
        pump = asyncio.create_task(self._pump(ws, q))
        try:
            async for raw in ws:
                self._on_inbound(raw)
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

    def _on_inbound(self, raw) -> None:
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
            self._on_command(name, args)   # only ever SUBMITS (non-blocking)
        except Exception as exc:  # never let one command kill the reader
            print(f"[ws] command {name!r} handler error: {exc}")

    # ── server lifecycle (own loop thread) ────────────────────────────
    async def _serve(self, host: str, port: int) -> None:
        self._stop_event = asyncio.Event()
        async with websockets.serve(self._handler, host, port):
            self._ready.set()
            await self._stop_event.wait()

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


__all__ = ["DemoWSServer", "CommandHandler"]
