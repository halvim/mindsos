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
            "  brain=%s type=%s kl=%s episodes=%d",
            device_id,
            brain.profile.device_type,
            brain.kl.global_metagraph().name,
            result.episodes[device_id],
        )
    if not result.ok:
        log.error("SMOKE FAILED: %d/4 Episodes", result.total_episodes)
        return 1
    log.info(
        "DM-1 SMOKE PASS: 4 device-instances up, %d/4 Episodes consolidated.",
        result.total_episodes,
    )

    if os.environ.get("DEMO_BOOTSTRAP_ONLY") == "1":
        # gate/CI mode — stop the ILs cleanly and exit 0
        for brain in result.brains.values():
            brain.il.stop()
        return 0

    log.info("Holding (DM-2+ will start sim + bus + WebSocket here). Ctrl-C to exit.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:  # pragma: no cover
        for brain in result.brains.values():
            brain.il.stop()
        return 0


if __name__ == "__main__":
    sys.exit(main())
