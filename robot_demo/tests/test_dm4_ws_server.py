"""DM-4 — WS server loopback test (real socket, no browser; needs websockets).

Skips if the ``websockets`` package isn't installed (the 3.10 sandbox may
lack it; the Linux gate has it). Validates the contract handshake + command
routing + FrameHub→client delivery end-to-end over a real WebSocket.
"""

from __future__ import annotations

import asyncio
import json

import pytest

websockets = pytest.importorskip("websockets")

from robot_demo.backend.frames import DemoEvents, FrameHub
from robot_demo.backend.ws_server import DemoWSServer


def test_ws_server_handshake_command_and_broadcast():
    hub = FrameHub()
    seen_cmds = []

    def on_command(name, args):
        seen_cmds.append((name, args))

    server = DemoWSServer(hub, on_command, beats_total=3)
    server.start(host="127.0.0.1", port=8799)

    async def client_flow():
        async with websockets.connect("ws://127.0.0.1:8799") as ws:
            # 1) hello on connect
            hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
            assert hello["type"] == "hello"
            assert hello["beats_total"] == 3
            assert hello["brains"] == ["mgr", "a1", "a2", "conv"]

            # 2) browser → server command is routed to the handler
            await ws.send(json.dumps(
                {"type": "command", "name": "place_order",
                 "args": {"lines": [{"item": "sheet"}]}}))

            # 3) a frame published from a "worker thread" reaches the client
            DemoEvents(hub).message("mgr", "arm1", "dispatch(move_to)")
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
            assert msg["type"] == "message"
            assert msg["from"] == "Orchestrator" and msg["to"] == "Arm1"

    try:
        asyncio.run(client_flow())
        # the command handler ran (give the loop a beat to deliver it)
        import time
        for _ in range(20):
            if seen_cmds:
                break
            time.sleep(0.05)
        assert seen_cmds == [("place_order", {"lines": [{"item": "sheet"}]})]
    finally:
        server.stop()
