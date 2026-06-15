"""DM-4 Seam A — outbound frame layer (plan §2.2, WS contract).

Two pieces, both decoupled from the ``websockets`` transport so they are
sandbox-testable without it:

* **FrameHub** — a thread→asyncio bridge. Brains run on IL worker threads,
  the bus on per-brain consumer threads, the sim on its clock thread; all of
  them call ``publish(frame)`` from *their* thread. The hub marshals each
  frame onto the WS event loop (``call_soon_threadsafe``) and fans it out to
  every connected client's ``asyncio.Queue``. This is the discipline that
  keeps socket I/O off the sim-clock thread (design-log PB-ZZ).

* **DemoEvents** — the single frame *shaper*. It owns the wire vocabulary so
  the rest of the backend speaks in brain ids: device-id → contract-id
  aliasing (``arm1→a1``, ``arm2→a2``), the ``message`` display-name map, and
  the WS-contract §3 transient discipline (a brain that should read *active*
  must carry ``active``/``flags`` in the frame it appears in; the UI's merge
  resets them to ``false``/``[]`` for any brain absent from a frame, so we
  only emit the brains that changed/are-active each beat).

Frame shapes mirror ``demo_ui/mock_ws_server.js`` exactly (the authoritative
reference emitter): ``hello`` / ``state`` / ``message`` / ``pose`` / ``reset``.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, Set

# device-id (backend) → contract brain-id (UI). mgr/conv are identical.
BRAIN_ALIAS: Dict[str, str] = {"arm1": "a1", "arm2": "a2", "mgr": "mgr", "conv": "conv"}

# device-id → message-panel display name (WS contract §2.4).
#: Sanitized party vocabulary (policy B): "Fleet" not "Global", "Library"
#: not "L2" (ROBOT_DEMO_IP_SANITIZATION.md). The wire shows behavior, not the
#: layer architecture.
DISPLAY_NAME: Dict[str, str] = {
    "mgr": "Orchestrator", "arm1": "Arm1", "arm2": "Arm2", "conv": "Conveyor",
    "user": "User", "fleet": "Fleet", "library": "Library",
    "demo": "Demonstration",
}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _display(name: str) -> str:
    return DISPLAY_NAME.get(name, name)


def _alias(device_id: str) -> str:
    return BRAIN_ALIAS.get(device_id, device_id)


class FrameHub:
    """Thread-safe publish → per-client asyncio fan-out (PB-ZZ)."""

    def __init__(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._clients: Set["asyncio.Queue[dict]"] = set()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind the WS event loop. Call once, from inside that loop."""
        self._loop = loop

    def register(self) -> "asyncio.Queue[dict]":
        """Add a client outbound queue (call on the loop thread)."""
        q: "asyncio.Queue[dict]" = asyncio.Queue(maxsize=1024)
        self._clients.add(q)
        return q

    def unregister(self, q: "asyncio.Queue[dict]") -> None:
        self._clients.discard(q)

    def client_count(self) -> int:
        return len(self._clients)

    def publish(self, frame: dict) -> None:
        """Publish a frame from ANY thread. No-op until a loop is bound."""
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        loop.call_soon_threadsafe(self._fanout, frame)

    def _fanout(self, frame: dict) -> None:  # runs on the loop thread
        for q in list(self._clients):
            try:
                q.put_nowait(frame)
            except asyncio.QueueFull:
                pass  # a stalled client never backs up the producers


class DemoEvents:
    """Frame shaper — the backend's only writer of UI frames.

    ``beat`` is advisory (the UI derives its own index from frame order, WS
    contract §7); we still send a monotonic ``beat`` for debuggability.
    ``cbeat`` (DM-6, UI coordination) is the 0-based global *storyline* beat —
    it advances only on a true beat transition (a titled ``state``), so the UI
    can render "Beat cbeat+1 / beats_total" + group the timeline by beat."""

    def __init__(self, hub: FrameHub) -> None:
        self._hub = hub
        self._beat = 0
        self._cbeat = -1  # first titled beat -> 0

    @staticmethod
    def hello_frame(beats_total: int = 7) -> dict:
        """The per-connection handshake (sent by the server on connect, not
        broadcast through the hub)."""
        return {
            "type": "hello", "scenario": "open-order",
            "brains": ["mgr", "a1", "a2", "conv"], "beats_total": beats_total,
        }

    def state(
        self,
        brains: Dict[str, Dict[str, Any]],
        *,
        title: Optional[str] = None,
        narr: Optional[str] = None,
        items: Optional[Dict[str, List[float]]] = None,
        eff: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Emit one cognitive beat. ``brains`` keyed by *device id*; only the
        brains that changed / are active this beat need be present (§3)."""
        bmap: Dict[str, Dict[str, Any]] = {}
        for device_id, fields in brains.items():
            f = dict(fields)
            f.setdefault("active", False)   # §3 transient — explicit every frame
            f.setdefault("flags", [])
            bmap[_alias(device_id)] = f
        if title is not None:
            self._cbeat += 1  # a titled state is a true beat transition (UI)
        frame: Dict[str, Any] = {
            "type": "state", "t": _now_ms(), "beat": self._beat,
            "cbeat": max(self._cbeat, 0), "brains": bmap,
        }
        self._beat += 1
        if title is not None:
            frame["title"] = title
        if narr is not None:
            frame["narr"] = narr
        if items is not None:
            frame["items"] = items
        if eff is not None:
            frame["eff"] = eff
        self._hub.publish(frame)
        return frame

    def message(self, frm: str, to: str, text: str) -> dict:
        """Emit one Seam-B inter-brain log line (device ids → display names)."""
        frame = {
            "type": "message", "from": _display(frm), "to": _display(to),
            "text": text, "t": _now_ms(),
        }
        self._hub.publish(frame)
        return frame

    def pose(
        self,
        items: Optional[Dict[str, List[float]]] = None,
        eff: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Emit a high-frequency pose update (cell view). ``items``/``eff`` are
        the UI's top-down ``[x, y]`` world coords; the projection lives in
        ``pose_frame`` (affine pending the UI coordinate-box confirmation)."""
        frame = {
            "type": "pose", "t": _now_ms(),
            "items": items or {}, "eff": eff or {"a1": None, "a2": None},
        }
        self._hub.publish(frame)
        return frame

    def resolve(
        self,
        *,
        brain: str,
        clause: str,
        stages: List[Dict[str, Any]],
        winner: Optional[int],
        item: Optional[str] = None,
        tube: Optional[int] = None,
    ) -> dict:
        """Emit a Plan ▸ Resolve narrowing frame (WS contract §5).

        ``stages`` = ``[{"cap": <label>, "cells": {0..8: "cand"|"win"|"out"}}]``
        (the 9→…→1 narrowing); ``winner`` = the chosen 3×3 cell index; ``tube``
        = the reference-object cell for a relational clause (or ``None``). All
        labels are behavior-level (policy B)."""
        frame: Dict[str, Any] = {
            "type": "resolve", "t": _now_ms(),
            "brain": _alias(brain), "clause": clause,
            "stages": stages, "winner": winner,
        }
        if item is not None:
            frame["item"] = item
        if tube is not None:
            frame["tube"] = tube
        self._hub.publish(frame)
        return frame

    def reset(self) -> dict:
        self._beat = 0
        self._cbeat = -1
        frame = {"type": "reset"}
        self._hub.publish(frame)
        return frame

    # ── DM-4 L5 export / Server panel (pure shapers — see note) ────────
    #
    # ``state_snapshot`` is a TARGETED reply to the requesting client
    # (design-log PB-16) and ``server_status`` is sent on connect + by the
    # heartbeat, so these are *pure shapers* (no ``hub.publish``): the ws
    # server decides whether to ``respond`` (one client) or broadcast.
    @staticmethod
    def snapshot_frame(snapshot: dict) -> dict:
        """Wrap a serialized L5 snapshot as the ``state_snapshot`` frame the
        UI downloads (WS contract / L5 export §B)."""
        return {"type": "state_snapshot", "snapshot": snapshot}


def server_status_frame(
    sessions: List[Dict[str, str]],
    *,
    uptime_s: int,
    storage_connected: bool = True,
    state_saved: bool = False,
    endpoint: Optional[str] = None,
) -> dict:
    """Shape the ``server_status`` vitals frame (IP-sanitized — design-log PB-3/4).

    Deviates from the originally-locked §D keys per the IP-sanitization addendum
    (later, load-bearing): **no ``mindsos_version``**; ``persistence.falkordb``
    → ``storage`` ("connected", never "Falkor"); ``globals_persisted`` →
    ``state_saved``; the raw ``user`` is dropped (the device-role display name
    is the only identity shown).

    ``sessions``: ``[{"device_id": .., "since": <iso8601>}, …]`` (device ids;
    mapped to display names here)."""
    shaped = [
        {"brain": _display(s["device_id"]), "since": s.get("since", "")}
        for s in sessions
    ]
    frame: Dict[str, Any] = {
        "type": "server_status",
        "t": _now_ms(),
        "storage": "connected" if storage_connected else "connecting",
        "state_saved": bool(state_saved),
        "uptime_s": int(uptime_s),
        "sessions": shaped,
    }
    if endpoint:
        frame["endpoint"] = endpoint
    return frame


__all__ = [
    "FrameHub", "DemoEvents", "BRAIN_ALIAS", "DISPLAY_NAME",
    "server_status_frame",
]
