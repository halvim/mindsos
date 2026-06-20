"""DM-3 — Seam C BodyHandle: per-embodied-brain handle over the shared sim.

**MuJoCo host only** (imports :mod:`sim_engine`). Each ``BodyHandle`` is a
thin façade the atomic capacities (:mod:`capacities`) close over — it
exposes the duck contract (``move_to`` / ``set_grip`` / ``sense_poses`` /
``diagnose`` / ``run_belt`` / ``stop_belt``) and routes to the single shared
:class:`SimEngine` (PB-KK). The live-motion wrapper (PB-F) lives in
``move_to``: cache-first, live-generate on a miss, honest motion dont-know
on a checklist-failing miss (:func:`live_motion.run_motion`).

One ``SimEngine`` + three handles (a1/a2/belt); ``build_body_runtime`` wires
them. The manager has no body.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .live_motion import MotionOutcome, run_motion
from .motion_cache import Trajectory, TrajectoryCache, make_key
from .motion_checklist import StructureSpec, atomic_checklist
from .pose_frame import EFF_BODIES, ITEM_BODIES
from .sim_engine import SLOT_A1, SLOT_A2, SimEngine, structure_spec

_PLAY_TIMEOUT_S = 30.0


class BodyHandle:
    """One embodied brain's view of the shared sim."""

    def __init__(
        self,
        engine: SimEngine,
        *,
        arm: Optional[int],
        slot: Optional[str],
        cache: TrajectoryCache,
        spec: StructureSpec,
    ) -> None:
        self.engine = engine
        self.arm = arm
        self.slot = slot
        self.cache = cache
        self.spec = spec

    # ── move_to (G-7 live-motion wrapper) ─────────────────────────────
    def _resolve_target(self, spec: Any) -> Tuple[List[float], str]:
        spec = spec or {}
        if "qpos" in spec:
            return list(spec["qpos"]), str(spec.get("key", "custom"))
        name = spec.get("named", "rest")
        return self.engine.named_target(self.arm, name), name

    def move_to(self, spec: Any) -> MotionOutcome:
        if self.arm is None:
            raise RuntimeError("conveyor BodyHandle has no move_to")
        spec = spec or {}
        # DM-5 ◆: an item/cell spec is a cartesian reach (pick/place); a
        # qpos/named spec is the DM-3 joint-space move.
        if "item" in spec or "cell" in spec:
            return self._reach_cartesian(spec)
        target_qpos, target_name = self._resolve_target(spec)
        key = make_key(self.arm, "move_to", target_name)

        def generate() -> Trajectory:
            qpos, body = self.engine.generate_arm_move(self.arm, target_qpos)
            return Trajectory(qpos, body)

        def checklist(traj: Trajectory):
            return atomic_checklist(traj.body, self.engine.bodies, self.arm, self.spec)

        def play(traj: Trajectory) -> None:
            self.engine.submit(self.slot, traj.qpos).result(timeout=_PLAY_TIMEOUT_S)

        return run_motion(self.cache, key, generate, play, checklist)

    def _reach_cartesian(self, spec: dict) -> MotionOutcome:
        """DM-5 ◆ cartesian reach to an item-grasp or shelf-cell pose (Linux-
        gated). Reuses the G-7 cache→gen→checklist→play|dont-know policy with a
        cartesian generate (``SimEngine.generate_arm_reach``)."""
        phase = spec.get("phase", "approach")
        if "item" in spec:
            item = spec["item"]
            xyz, R = self.engine.item_grasp_target(self.arm, item, phase)
            key = make_key(self.arm, "pick", f"{item}:{phase}")
        else:
            cell = spec["cell"]
            xyz, R = self.engine.cell_target(self.arm, cell, phase)
            key = make_key(self.arm, "place", f"{cell}:{phase}")

        def generate() -> Trajectory:
            qpos, body = self.engine.generate_arm_reach(self.arm, xyz, R)
            return Trajectory(qpos, body)

        def checklist(traj: Trajectory):
            return atomic_checklist(traj.body, self.engine.bodies, self.arm, self.spec)

        def play(traj: Trajectory) -> None:
            self.engine.submit(self.slot, traj.qpos).result(timeout=_PLAY_TIMEOUT_S)

        return run_motion(self.cache, key, generate, play, checklist)

    # ── grip / sense / diagnose / belt ────────────────────────────────
    def set_grip(self, engage: bool, obj: Optional[str] = None) -> Dict:
        return self.engine.set_grip(self.arm, engage, obj=obj)

    def sense_poses(self) -> Dict[str, List[float]]:
        poses = self.engine.read_poses()
        want = set(ITEM_BODIES.values()) | set(EFF_BODIES.values())
        return {k: v for k, v in poses.items() if k in want}

    def diagnose(self) -> Dict:
        return self.engine.probe_actuators(self.arm)

    def run_belt(self, direction: int, distance: float) -> Dict:
        self.engine.move_belt(direction, distance).result(timeout=_PLAY_TIMEOUT_S)
        return {"displaced": float(direction) * float(distance)}

    def stop_belt(self) -> Dict:
        return {"displaced": 0.0, "stopped": True}


def build_body_runtime() -> Tuple[SimEngine, Dict[str, BodyHandle]]:
    """Build + start the single shared SimEngine and the per-device handles.

    Returns ``(engine, {device_id: BodyHandle})`` for the embodied devices
    (``arm1``/``arm2``/``conv``); the manager has no body.
    """
    engine = SimEngine()
    engine.start()
    cache = TrajectoryCache()
    spec = structure_spec()
    handles = {
        "arm1": BodyHandle(engine, arm=1, slot=SLOT_A1, cache=cache, spec=spec),
        "arm2": BodyHandle(engine, arm=2, slot=SLOT_A2, cache=cache, spec=spec),
        "conv": BodyHandle(engine, arm=None, slot=None, cache=cache, spec=spec),
    }
    return engine, handles


__all__ = ["BodyHandle", "build_body_runtime"]
