"""DM-2 — Local seeds per brain (plan §3.3, F4-min embodiment).

Each brain writes its OWN Local ``capacity-state`` via
``make_writeable(device_kl, brain_session)`` — no admin. The ADR-0180
gate only fires on Global writes, so a normal brain session (USER_CAPS
empty) writes its Local with no ``CAN_WRITE_GLOBAL`` (Phase-48 PB-10).

**Encoding (PB-W, design log §10):** the ``capacity-state`` schema is a
single ``CapacitySnapshot`` NodeType with **zero EdgeTypes**, so the
embodiment "subgraph" (BodyPart/EndEffector nodes + has-part/provides
edges) cannot be built as typed nodes+edges without a forbidden schema
edit. Instead each brain's embodiment is ONE ``CapacitySnapshot`` node
whose structured ``value`` carries parts / affordances / reach. The DM-3
``validate.feasibility`` capacity reads this bag (it never walked edges).
Limitation tracked as F8 (a real ``embodiment`` role-graph).

Idempotent: a stable ``node_id`` per brain; re-seeding a present node is
a no-op (get-or-create), so a re-boot / re-seed leaves one snapshot.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from mindsos_capacity.context import make_writeable
from mindsos_knowledge.metagraph_view import MetagraphView

ROLE_CAPACITY_STATE = "capacity-state"
SNAPSHOT_TYPE = "CapacitySnapshot"


def embodiment_node_id(device_id: str) -> str:
    return f"embodiment:{device_id}"


#: F4-min embodiment per device (plan §3.3). Property-encoded (PB-W).
#: ``parts``/``provides``/``reach`` are the feasibility-gate inputs;
#: ``availability`` lists the §4 capacities this body will expose (DM-3).
EMBODIMENT: Dict[str, Dict[str, Any]] = {
    "arm1": {
        "body": "a1",
        "parts": [
            {"part": "Arm", "name": "panda_1"},
            {"part": "EndEffector", "name": "suction_tip",
             "provides": ["grasp:suction"]},
        ],
        "provides": ["grasp:suction"],
        "reach": ["shelf_L", "belt_a1"],
        "availability": ["a1.move_to", "a1.suction_set", "a1.pick",
                         "a1.place_at_cell"],
    },
    "arm2": {
        "body": "a2",
        "parts": [
            {"part": "Arm", "name": "panda_2"},
            {"part": "EndEffector", "name": "jaw_2f85",
             "provides": ["grasp:jaw"]},
        ],
        "provides": ["grasp:jaw"],
        "reach": ["shelf_R", "belt_a2"],
        "availability": ["a2.move_to", "a2.jaw_set", "a2.pick",
                         "a2.place_at_cell"],
    },
    "conv": {
        "body": "conv",
        "parts": [{"part": "Belt", "name": "belt_main"}],
        "provides": ["move:belt(belt_a1<->belt_mid<->belt_a2)"],
        "reach": ["belt_a1", "belt_mid", "belt_a2"],
        "staging": {"feeder": "belt_a1", "collector": "belt_a2",
                    "mid_band": "belt_mid"},
        "availability": ["conv.run", "conv.stop", "conv.stage_at"],
    },
    # mgr has no body — cognitive availability only (no parts/affordances).
    "mgr": {
        "body": None,
        "parts": [],
        "provides": [],
        "reach": [],
        "availability": ["perception.ingest_order", "comprehension.match_items",
                         "planning.fulfill_order", "process.execute_plan"],
    },
}


def _capacity_state_graph(kl: Any, device_id: str):
    """The brain's own Local capacity-state graph (read side)."""
    local_mg = kl.local_metagraph(device_id)
    return MetagraphView(local_mg).graphs_by_role(ROLE_CAPACITY_STATE)[0]


def seed_local_embodiment(
    kl: Any, session: Any, device_id: str
) -> bool:
    """Get-or-create the brain's embodiment snapshot in its Local.

    Returns ``True`` if a node was written, ``False`` if already present
    (idempotent re-seed). Writes through ``make_writeable`` (the brain's
    own session, Local scope).
    """
    spec = EMBODIMENT.get(device_id)
    if spec is None:
        raise KeyError(f"no embodiment spec for device {device_id!r}")

    node_id = embodiment_node_id(device_id)
    writeable = make_writeable(kl, session)
    if writeable is None:
        raise RuntimeError("no KL bound; make_writeable returned None")
    handle = writeable(role=ROLE_CAPACITY_STATE, scope="local")
    graph = handle.graph()

    if node_id in graph.nodes:
        return False  # idempotent — already seeded
    graph.add_node(
        dict(spec),
        SNAPSHOT_TYPE,
        properties={
            "snapshot_kind": "embodiment",
            "device": device_id,
            "embodied": bool(spec.get("body")),
        },
        node_id=node_id,
    )
    return True


def read_local_embodiment(kl: Any, device_id: str) -> Optional[Dict[str, Any]]:
    """Read back the embodiment bag (visibility test / feasibility input)."""
    g = _capacity_state_graph(kl, device_id)
    node = g.nodes.get(embodiment_node_id(device_id))
    return None if node is None else node.value


__all__ = [
    "EMBODIMENT",
    "ROLE_CAPACITY_STATE",
    "SNAPSHOT_TYPE",
    "embodiment_node_id",
    "seed_local_embodiment",
    "read_local_embodiment",
]
