"""reset.py — between-run reset (G-11 / PB-H). DM-1 stub.

The empty-start thesis is really a *reset* requirement: every rehearsal
contaminates the Locals + the in-memory CLs (taught composites, episodes,
gaps, traces). The chosen model (G-11) is **restart-based**:

  * In-memory CLs + in-memory KLs clear on process restart (DM-1 holds all
    L2 in memory, so a restart is already a full wipe).
  * ``reset.py`` additionally wipes each device's Local run-state nodes
    (taught artifacts, episodes, gaps, traces) with an explicit keep-list
    for the §3.3 seeds, leaving Global seeds intact — needed once DM-2
    persists per-device KLs to Falkor.
  * All run-scoped nodes are tagged with a ``run_id`` so wipe and the
    beat-6 recap are both run-scoped.

Surgical in-place CL deregistration is explicitly NOT built (Phase-50:
de-install is marker-only; new mechanism, no payoff).

DM-1 status: STUB. At DM-1 there is no persisted Local run-state to wipe
(KLs are in-memory; a restart is the reset). The function shapes below
freeze the G-11 contract; the wipe body lands in DM-2 alongside the
per-device Falkor persistence (PB-J).
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

log = logging.getLogger("robot_demo.reset")

#: Local roles whose seed content must SURVIVE a reset (§3.3). Run-state
#: roles (episodic_memories, problem-trace, learned composites in
#: capacity-state) are wiped; these are kept.
KEEP_ROLES_LOCAL: tuple[str, ...] = (
    "capacity-state",  # seeds kept; learned LearnedComposite nodes wiped (DM-2 filter)
)


def restart_reset_note() -> str:
    """The operator runbook line (DM-1): reset == process restart."""
    return (
        "Reset = `docker compose restart demo-backend` (in-memory CLs + KLs "
        "clear on restart). Per-device Global seeds are re-installed by "
        "bootstrap. Run-scoped Local wipe lands in DM-2."
    )


def wipe_local_run_state(
    brain: Any,
    *,
    run_id: str | None = None,
    keep_roles: Iterable[str] = KEEP_ROLES_LOCAL,
) -> int:
    """DM-2 (stub at DM-1): wipe run-scoped Local nodes for one brain.

    Returns the number of nodes removed. At DM-1 this is a no-op (KLs are
    in-memory; restart is the reset) — the body is implemented once DM-2
    persists per-device Locals and tags run-scoped nodes with ``run_id``.
    """
    log.info(
        "wipe_local_run_state(%s, run_id=%s): no-op at DM-1 (restart is the "
        "reset); keep_roles=%s",
        getattr(brain, "device_id", "?"),
        run_id,
        tuple(keep_roles),
    )
    return 0


__all__ = ["wipe_local_run_state", "restart_reset_note", "KEEP_ROLES_LOCAL"]
