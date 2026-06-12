"""demo_backend entrypoint — ``python -m demo_backend.main``.

DM-1: run the bootstrap + smoke, print a clear PASS/FAIL, then either
exit (``DEMO_BOOTSTRAP_ONLY=1`` — for the compose gate / CI) or idle so
the container stays up (DM-2+ will start the sim loop + BrainBus + the
WebSocket server here).
"""

from __future__ import annotations

import logging
import os
import sys
import time

from .bootstrap import bootstrap

log = logging.getLogger("robot_demo")


def _configure_logging() -> None:
    logging.basicConfig(
        level=os.environ.get("DEMO_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    log.info("demo_backend DM-1 bootstrap starting (4 device-instances)…")
    try:
        result = bootstrap()
    except Exception:  # noqa: BLE001 — surface the full traceback + exit nonzero
        log.exception("BOOTSTRAP FAILED")
        return 1

    for device_id, brain in result.brains.items():
        log.info(
            "  brain=%s type=%s kl=%s episodes=%d bundles=%s seeded_local=%s",
            device_id,
            brain.profile.device_type,
            brain.kl.global_metagraph().name,
            result.episodes[device_id],
            (result.bundles or {}).get(device_id),
            (result.seeded_local or {}).get(device_id),
        )
    if not result.ok:
        log.error("SMOKE FAILED: %d/4 Episodes", result.total_episodes)
        return 1
    log.info(
        "DM-1 SMOKE PASS: 4 device-instances up, %d/4 Episodes consolidated.",
        result.total_episodes,
    )
    # DM-2 markers (asserted by run_linux_tests.sh).
    log.info(
        "DM-2 BUNDLES INSTALLED: %s",
        {d: result.bundles[d] for d in result.bundles} if result.bundles else {},
    )
    if all((result.seeded_local or {}).get(d) is not None for d in result.brains):
        log.info("DM-2 LOCAL SEEDS: %s", result.seeded_local)
    log.info(
        "DM-2 GLOBAL PERSIST: %s | G-5 EPISODE ROUND-TRIP: %s",
        "falkor" if result.persisted_global else "in-memory(fallback)",
        result.episode_roundtrip or "skipped(in-memory)",
    )

    if os.environ.get("DEMO_BOOTSTRAP_ONLY") == "1":
        # gate/CI mode — stop the ILs cleanly and exit 0
        for brain in result.brains.values():
            brain.il.stop()
        return 0

    # ── DM-4: BrainBus + comms + WS server (Seam A/B) ──────────────────
    server = None
    bus = None
    if os.environ.get("DEMO_NO_WS") != "1":
        server, bus = _start_ws(result)

    log.info("Holding (Ctrl-C to exit).")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:  # pragma: no cover
        if server is not None:
            server.stop()
        if bus is not None:
            bus.stop()
        for brain in result.brains.values():
            brain.il.stop()
        return 0


def _start_ws(result):
    """DM-4 — wire the BrainBus + comms + pose stream and serve the brains
    WebSocket. Returns ``(server, bus)``."""
    from .bus import BrainBus
    from .frames import DemoEvents, FrameHub
    from .wiring import (
        make_live_run_atomic,
        make_status_provider,
        wire_demo,
        wire_pose_stream,
    )
    from .ws_server import DemoWSServer

    bus = BrainBus()
    hub = FrameHub()
    events = DemoEvents(hub)

    # The live move_to invoke needs the SimEngine (qpos spec); with no body
    # (DEMO_BODY=0) wire_demo's stub run_atomic keeps the flow completing.
    run_atomic = (
        make_live_run_atomic(result.sim_engine)
        if result.sim_engine is not None else None
    )
    on_command = wire_demo(result.brains, bus, events, run_atomic=run_atomic)
    if result.sim_engine is not None:
        wire_pose_stream(result.sim_engine, events)
        log.info("DM-4 POSE STREAM wired (sim → projected pose frames).")

    # DM-4 Server panel: real sessions + uptime + storage state (sanitized).
    endpoint = os.environ.get("DEMO_WS_ENDPOINT")  # e.g. wss://brains.sanmyaku.com
    status_provider = make_status_provider(result, endpoint=endpoint)

    host = os.environ.get("DEMO_WS_HOST", "0.0.0.0")
    port = int(os.environ.get("DEMO_WS_PORT", "8765"))
    server = DemoWSServer(hub, on_command, beats_total=7,
                          status_provider=status_provider)
    server.start(host=host, port=port)
    log.info("DM-4 WS SERVER LISTENING ws://%s:%d "
             "(open presentation.html?live=ws://<host>:%d)", host, port, port)
    return server, bus


if __name__ == "__main__":
    sys.exit(main())
