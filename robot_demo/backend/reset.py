"""reset.py — between-run reset (G-11 / PB-H).

The empty-start thesis is really a *reset* requirement: every rehearsal
contaminates the Locals + the in-memory CLs (taught composites, episodes,
gaps, traces). The chosen model (G-11) is **restart-based**:

  * In-memory CLs + in-memory **Locals** clear on process restart
    (PB-Z: Locals are NOT persisted at DM-2, so a restart is already a
    full Local wipe). Per-device **Globals** persist in Falkor — the
    §3.x seeds survive a restart, which is exactly the reset contract
    (seeds kept, run-state gone).
  * ``wipe_local_run_state`` is the *without-restart* path: it removes a
    live brain's run-state Local nodes (Episodes/Memories, and DM-6
    LearnedComposite nodes in capacity-state) while keeping the §3.3
    embodiment seed.
  * Run-scoped nodes may carry a ``run_id`` property so wipe and the
    beat-6 recap are both run-scoped; absent a filter, all run-state is
    wiped.

Surgical in-place CL deregistration is explicitly NOT built (Phase-50:
de-install is marker-only; new mechanism, no payoff).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from mindsos_knowledge.metagraph_view import MetagraphView

from .seeds import embodiment_node_id

log = logging.getLogger("robot_demo.reset")

ROLE_EPISODIC = "episodic_memories"
ROLE_CAPACITY_STATE = "capacity-state"

#: NodeTypes considered run-state (wiped). The embodiment seed is a
#: CapacitySnapshot too, so capacity-state is filtered by node_id keep-list
#: (the embodiment node) rather than by type.
_RUN_STATE_EPISODIC_TYPES = {"Episode", "Memory"}


def restart_reset_note() -> str:
    """The operator runbook line: reset == process restart."""
    return (
        "Reset = `docker compose restart demo-backend` (in-memory CLs + "
        "Locals clear on restart; per-device Global seeds reload from "
        "Falkor). `wipe_local_run_state(brain)` is the no-restart path."
    )


def _matches_run(node: Any, run_id: Optional[str]) -> bool:
    """A node is in scope if no run_id filter is given, or its run_id
    property matches."""
    if run_id is None:
        return True
    return node.properties.get("run_id") == run_id


def wipe_local_run_state(
    brain: Any,
    *,
    run_id: Optional[str] = None,
) -> int:
    """Wipe run-scoped Local nodes for one live brain; return the count.

    Removes Episodes/Memories from ``episodic_memories`` and any non-seed
    nodes from ``capacity-state`` (DM-6 LearnedComposite etc.), keeping the
    §3.3 embodiment snapshot. Optionally restricted to a single ``run_id``.
    """
    kl = brain.kl
    device_id = brain.device_id
    local_mg = kl.local_metagraph(device_id)
    view = MetagraphView(local_mg)
    keep_id = embodiment_node_id(device_id)
    removed = 0

    ep_graphs = view.graphs_by_role(ROLE_EPISODIC)
    if ep_graphs:
        g = ep_graphs[0]
        for nid in [
            nid for nid, n in g.nodes.items()
            if getattr(n, "type_name", None) in _RUN_STATE_EPISODIC_TYPES
            and _matches_run(n, run_id)
        ]:
            del g.nodes[nid]
            removed += 1

    cs_graphs = view.graphs_by_role(ROLE_CAPACITY_STATE)
    if cs_graphs:
        g = cs_graphs[0]
        for nid in [
            nid for nid, n in g.nodes.items()
            if nid != keep_id and _matches_run(n, run_id)
        ]:
            del g.nodes[nid]
            removed += 1

    log.info(
        "wipe_local_run_state(%s, run_id=%s): removed %d run-state node(s); "
        "kept embodiment seed %s",
        device_id, run_id, removed, keep_id,
    )
    return removed


__all__ = ["wipe_local_run_state", "restart_reset_note", "ROLE_EPISODIC",
           "ROLE_CAPACITY_STATE"]
