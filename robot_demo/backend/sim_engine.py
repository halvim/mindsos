"""DM-3 — SimEngine: the single shared-``Cell`` sim owner (PB-KK/SS/VV).

**MuJoCo host only.** Imports ``sim/motion.py`` (which does ``import mujoco``
at module top), so this module is un-importable in the 3.10 / no-MuJoCo
sandbox. Everything MindsOS-facing lives in MuJoCo-free modules
(``capacities``/``motion_cache``/``motion_checklist``/``live_motion``/
``pose_frame``) per PB-TT; this file is gated on the Linux container.

Architecture (design log §15):
  * **One** ``Cell`` holds BOTH arms + the belt (PB-KK) — three Cells would
    put a1/a2 in separate physics worlds and kill the cross-belt handoff.
  * The engine **owns the step clock** on its own thread and replays
    trajectories from a **per-actuator slot** (a1 / a2 / belt) — concurrency
    for DM-5 belt+arm interleave (PB-SS); DM-3 drives one slot at a time.
  * The live tick is **kinematic** (set qpos → ``mj_forward`` → capture),
    items pinned — the verified clip recipe; ``mj_step`` is reserved for
    explicit settle/drop (PB-VV). Each captured frame is throttled to the
    authored ``dt = timestep × CAP_EVERY`` (the PB-RR jitter nominal).
  * Heavy IK **generation** runs on a SCRATCH ``Cell`` (separate ``MjData``)
    so it never races the live tick (PB-E); the result is replayed onto the
    live slot.
  * ``freeze_joint`` clamps a joint in the apply-step so commanded ≠ actual
    (fault injection, PB-NN — a frozen actuator is invisible under pure
    kinematic drive otherwise).

``sim/`` is wrapped, never edited (PB-QQ): ``sys.path``-insert + ``import
motion``; we drive ``Cell`` primitives and read ``c.frames``; ``_save`` is
never called.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from concurrent.futures import Future
from typing import Dict, List, Optional, Tuple

import numpy as np

# ── wrap sim/ (PB-QQ) — path insert, no edits ─────────────────────────
_SIM_DIR = os.environ.get(
    "ROBOT_DEMO_SIM_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sim"),
)
if _SIM_DIR not in sys.path:
    sys.path.insert(0, _SIM_DIR)

import mujoco  # noqa: E402  (only reachable on the MuJoCo host)
import geom_config as G  # noqa: E402
import motion as M  # noqa: E402  (the shipped Cell + primitives)
from build_cell import HOME  # noqa: E402

from .motion_checklist import StructureSpec

CAP_EVERY = M.CAP_EVERY  # capture cadence (frames every N steps)

#: actuator-slot ids
SLOT_A1 = "a1"
SLOT_A2 = "a2"
SLOT_BELT = "belt"


def structure_spec() -> StructureSpec:
    """Build the checklist :class:`StructureSpec` from ``geom_config``."""
    return StructureSpec.from_geom_config(G)


def _free_item_bodies(cell) -> List[int]:
    """Body ids with a free joint (the belt items) — the ``pin_loose`` set."""
    out = []
    for b in range(cell.m.nbody):
        ja = cell.m.body_jntadr[b]
        if ja >= 0 and cell.m.jnt_type[ja] == mujoco.mjtJoint.mjJNT_FREE:
            out.append(b)
    return out


class SimEngine:
    """Single shared-``Cell`` owner + clock thread + per-actuator slots."""

    def __init__(self, *, hz: Optional[float] = None) -> None:
        self._cell = M.Cell()
        # Clip recipe start: pin every belt item at rest, let the arms
        # settle, then clear the capture buffers (design log; MOTION_STATE §5).
        self._cell.pin_loose()
        self._cell.step(20)
        self._cell.frames = []
        self._cell.events = []
        self._scratch = M.Cell()  # generation sandbox (separate MjData)

        self._dt = (self._cell.m.opt.timestep * CAP_EVERY) if hz is None else (1.0 / hz)
        self._lock = threading.RLock()
        self._slots: Dict[str, Tuple[List, Future]] = {}  # id -> (frames, future)
        self._frozen: Dict[str, Dict[int, float]] = {SLOT_A1: {}, SLOT_A2: {}}
        self._subs: List = []           # pose-stream callbacks(frame, bodies)
        self._run = False
        self._thread: Optional[threading.Thread] = None
        self.bodies: List[str] = list(self._cell.bodies)
        self.jitter_samples: List[float] = []

    # ── lifecycle ─────────────────────────────────────────────────────
    def start(self) -> None:
        if self._run:
            return
        self._run = True
        self._thread = threading.Thread(target=self._loop, name="sim-clock", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._run = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def subscribe(self, cb) -> None:
        """Register a pose-stream callback ``cb(frame_list, bodies)`` (DM-4)."""
        self._subs.append(cb)

    # ── the clock loop (PB-RR jitter nominal) ─────────────────────────
    def _loop(self) -> None:
        next_t = time.perf_counter()
        last = next_t
        while self._run:
            with self._lock:
                self._apply_active_slots()
                mujoco.mj_forward(self._cell.m, self._cell.d)
                self._cell.capture()
                frame = self._cell.frames[-1]
            for cb in list(self._subs):
                try:
                    cb(frame, self.bodies)
                except Exception:
                    pass
            now = time.perf_counter()
            self.jitter_samples.append((now - last) * 1000.0)
            last = now
            next_t += self._dt
            sleep = next_t - time.perf_counter()
            if sleep > 0:
                time.sleep(sleep)
            else:
                next_t = time.perf_counter()  # fell behind; resync

    def _apply_active_slots(self) -> None:
        """Pop one frame from every active slot, apply it (freeze-clamped)."""
        done = []
        for sid, (frames, fut) in self._slots.items():
            if not frames:
                done.append((sid, fut))
                continue
            self._apply_frame(sid, frames.pop(0))
        for sid, fut in done:
            self._slots.pop(sid, None)
            if not fut.done():
                fut.set_result(True)

    def _apply_frame(self, sid: str, frame) -> None:
        if sid in (SLOT_A1, SLOT_A2):
            arm = 1 if sid == SLOT_A1 else 2
            A = self._cell.arm[arm]
            q = np.asarray(frame, float).copy()
            for j, fv in self._frozen[sid].items():  # PB-NN clamp
                if 0 <= j < len(q):
                    q[j] = fv
            self._cell.d.qpos[A["qadr"]] = q
            for j, x in enumerate(A["act"]):
                self._cell.d.ctrl[x] = q[j]
        elif sid == SLOT_BELT:
            for bid, x, y, z in frame:
                adr = self._cell.qadr_of(bid)
                self._cell.d.qpos[adr:adr + 3] = [x, y, z]
        self._cell._apply_attach()

    # ── submit a trajectory into a slot, await drain ──────────────────
    def submit(self, sid: str, frames: List) -> Future:
        fut: Future = Future()
        with self._lock:
            if sid in self._slots and not self._slots[sid][1].done():
                self._slots[sid][1].set_result(False)  # supersede
            self._slots[sid] = (list(frames), fut)
        return fut

    # ── fault injection (PB-NN) ───────────────────────────────────────
    def freeze_joint(self, arm: int, joint_index: int) -> None:
        sid = SLOT_A1 if arm == 1 else SLOT_A2
        with self._lock:
            A = self._cell.arm[arm]
            self._frozen[sid][joint_index] = float(self._cell.d.qpos[A["qadr"]][joint_index])

    def clear_freezes(self, arm: Optional[int] = None) -> None:
        with self._lock:
            for sid in ([SLOT_A1 if arm == 1 else SLOT_A2] if arm else [SLOT_A1, SLOT_A2]):
                self._frozen[sid].clear()

    # ── reads ─────────────────────────────────────────────────────────
    def read_poses(self) -> Dict[str, List[float]]:
        with self._lock:
            return {
                self.bodies[b]: [round(float(x), 4)
                                 for x in (*self._cell.d.xpos[b], *self._cell.d.xquat[b])]
                for b in range(self._cell.m.nbody)
            }

    def arm_qpos(self, arm: int) -> List[float]:
        with self._lock:
            return [float(x) for x in self._cell.d.qpos[self._cell.arm[arm]["qadr"]]]

    # ── generation (heavy IK on the SCRATCH cell — off the live tick) ──
    def _capture_run(self, scratch, fn, arm: int) -> Tuple[List, List]:
        """Run ``fn(scratch)`` recording (arm-qpos frame, body frame) at the
        capture cadence. Returns (qpos_frames, body_frames)."""
        A = scratch.arm[arm]
        qframes: List = []

        def sync(c):
            if c._k % CAP_EVERY == 0:
                qframes.append([float(x) for x in c.d.qpos[A["qadr"]]])

        scratch._sync = sync
        scratch.frames = []
        scratch.events = []
        fn(scratch)
        scratch._sync = None
        return qframes, [list(f) for f in scratch.frames]

    def generate_arm_move(self, arm: int, target_qpos: List[float],
                          steps: int = 200) -> Tuple[List, List]:
        """Joint-space move (smooth, branch-stable) from the live pose to a
        verified config (DM-3 targets = clip rest/home configs). Generated on
        the scratch cell seeded to the live state."""
        with self._lock:
            seed = self._cell.d.qpos.copy()
        self._scratch.d.qpos[:] = seed
        mujoco.mj_forward(self._scratch.m, self._scratch.d)
        tgt = np.asarray(target_qpos, float)
        return self._capture_run(
            self._scratch, lambda c: c.move_to_q(arm, tgt, steps=steps), arm
        )

    def named_target(self, arm: int, name: str) -> List[float]:
        """Resolve a verified named target config for DM-3 move_to."""
        if name == "home":
            return list(HOME)
        if name in ("rest", "ready"):
            box = "box1" if arm == 1 else "box2"
            with self._lock:
                q = self._cell.rest_pose(arm, box)
            if q is None:
                raise RuntimeError(f"no rest pose for arm {arm}")
            return [float(x) for x in q]
        raise KeyError(f"unknown named target {name!r}")

    # ── diagnose probe (commanded vs actual; PB-NN) ───────────────────
    def probe_actuators(self, arm: int, delta: float = 0.10, steps: int = 30,
                        tol: float = 0.02) -> Dict:
        """Command a small per-joint delta and compare commanded vs actual.

        A frozen joint (``freeze_joint``) is clamped in the apply-step, so it
        won't reach the commanded delta → detected honestly. Returns the arm
        to its start pose afterwards (non-destructive probe)."""
        sid = SLOT_A1 if arm == 1 else SLOT_A2
        A = self._cell.arm[arm]
        q0 = np.asarray(self.arm_qpos(arm), float)
        lo, hi = np.asarray(A["lo"], float), np.asarray(A["hi"], float)
        target = np.clip(q0 + delta, lo, hi)

        def ramp(a, b):
            return [[float(v) for v in (1 - t) * a + t * b]
                    for t in np.linspace(0, 1, steps)]

        self.submit(sid, ramp(q0, target)).result(timeout=10)
        actual = np.asarray(self.arm_qpos(arm), float)
        commanded = np.abs(target - q0) > (tol / 2)
        missed = np.abs(actual - target) > tol
        frozen = [int(j) for j in range(len(q0)) if commanded[j] and missed[j]]
        deltas = {f"a{arm}_joint{j + 1}": round(float(abs(actual[j] - target[j])), 4)
                  for j in frozen}
        self.submit(sid, ramp(actual, q0)).result(timeout=10)  # restore
        return {
            "frozen_joints": [f"a{arm}_joint{j + 1}" for j in frozen],
            "deltas": deltas,
        }

    # ── grip (attach-on-valid-contact; proximity-gated) ───────────────
    def set_grip(self, arm: int, engage: bool, obj: Optional[str] = None) -> Dict:
        with self._lock:
            A = self._cell.arm[arm]
            sid = A["sid"]
            if not engage:
                if obj:
                    self._cell.detach(obj)
                return {"attached": False}
            target = obj or ("box1" if arm == 1 else "box2")
            tcp = self._cell.d.site_xpos[sid].copy()
            oc = self._cell.d.xpos[self._cell.bid(target)].copy()
            gap = float(np.linalg.norm(tcp - oc))
            if gap > 0.30:  # proximity gate — no fake grab from afar
                return {"attached": False, "gap_mm": round(gap * 1000)}
            self._cell.attach_tcp(target, sid)
            return {"attached": True, "obj": target, "gap_mm": round(gap * 1000)}

    # ── belt sweep (PB-PP — extracted from combo_load_convey) ─────────
    def move_belt(self, direction: int, distance: float, steps: int = 120) -> Future:
        """Move every free belt item by ``direction*distance`` (clamped to the
        belt span), the verified kinematic sweep. Returns a slot future."""
        with self._lock:
            items = _free_item_bodies(self._cell)
            starts = {}
            for b in items:  # detach pins so they can move
                self._cell.detach(self._cell.bodies[b])
                adr = self._cell.qadr_of(b)
                starts[b] = self._cell.d.qpos[adr:adr + 3].copy()
        disp_total = float(direction) * float(distance)
        frames: List = []
        for i in range(steps):
            al = 0.5 - 0.5 * np.cos(np.pi * (i + 1) / steps)
            frame = []
            for b, s0 in starts.items():
                x = float(np.clip(s0[0] + al * disp_total, G.BELT_X0 + 0.18, G.BELT_X1 - 0.18))
                frame.append((b, x, float(s0[1]), float(s0[2])))
            frames.append(frame)
        return self.submit(SLOT_BELT, frames)


__all__ = ["SimEngine", "structure_spec", "SLOT_A1", "SLOT_A2", "SLOT_BELT", "CAP_EVERY"]
