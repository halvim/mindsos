"""DM-3 — atomic capacities + body adapter + live motion + fault injection.

Two layers (mirrors test_dm1/test_dm2):
  * **Core** (any host, incl. the 3.10 / no-MuJoCo sandbox): the MindsOS-
    facing half (PB-TT) — atomic-capacity registration + invoke against the
    real ``mindsos_capacity``, the diagnose→Local-gap write (PB-NN/K), the
    subset checklist, the live-motion miss/dont-know policy, the pose
    projection, and the bootstrap body-guard skip.
  * **Integration** (MuJoCo host only): the shared SimEngine + BodyHandle —
    each atomic moves the live sim checklist-verified, the fault switch is
    detected, the belt sweeps, and the clock jitter is measured. Skipped
    where ``mujoco`` can't import.

DM-3 gate (plan §8): each atomic capacity moves the live sim, checklist-
verified; zero ``mindsos_*`` / ``sim/`` edits (additive registration only);
the DM-1/DM-2 bootstrap gate stays green.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.metagraph_view import MetagraphView

from robot_demo.backend.installers import install_core_datastates
from robot_demo.backend import capacities as C
from robot_demo.backend.capacities import (
    atomic_capacity_iris,
    register_embodied_capacities,
    DS_POSE_TARGET, DS_MOTION_DONE, DS_GRIP_CMD, DS_GRIP_STATE,
    DS_DIAG_REQUEST, DS_WORLD_FACT, DS_DIAG_REPORT, DS_BELT_CMD, DS_BELT_DONE,
)
from robot_demo.backend.live_motion import MotionOutcome, run_motion
from robot_demo.backend.motion_cache import TrajectoryCache, Trajectory, make_key
from robot_demo.backend.motion_checklist import StructureSpec, atomic_checklist


# ── fixtures ──────────────────────────────────────────────────────────
class _DuckSession:
    def __init__(self, uid: str) -> None:
        self.user_id = uid
        self.session_id = f"sess-{uid}"
        self.actor_role = "user"
        self.capabilities = frozenset()

    def has(self, capability: str) -> bool:
        return True


class _FakeBody:
    """Canned BodyHandle for the MuJoCo-free path."""

    def __init__(self, frozen=None):
        self._frozen = list(frozen or [])

    def move_to(self, spec):
        return MotionOutcome.done(12, cache_hit=False)

    def set_grip(self, engage, obj=None):
        return {"attached": bool(engage)}

    def sense_poses(self):
        return {"box1": [0.7, -0.6, 0.5, 1, 0, 0, 0], "tube1": [1.1, -0.6, 0.55, 1, 0, 0, 0]}

    def diagnose(self):
        return {"frozen_joints": list(self._frozen),
                "deltas": {j: 0.1 for j in self._frozen}}

    def run_belt(self, direction, distance):
        return {"displaced": float(direction) * float(distance)}

    def stop_belt(self):
        return {"displaced": 0.0, "stopped": True}


def _cl():
    kl = KnowledgeLayer.bootstrap()
    cl = CapacityLayer(kl=kl)
    install_core_datastates(cl)
    return kl, cl


def _spec():
    return StructureSpec(arm_x={1: 0.0, 2: 3.0}, shelf_y={1: -1.2, 2: -1.2},
                         col_dx=0.18, shelf_depth=0.3, row_z0=0.8, row_dz=0.2,
                         belt_x0=-2.0, belt_x1=2.0, belt_y=0.4, belt_half_w=0.25)


# ── core: registration + invoke ───────────────────────────────────────
def test_atomic_roster_per_device_type():
    assert atomic_capacity_iris("arm-suction") == (
        "capacity:mechanism:a1.move_to",
        "capacity:mechanism:a1.suction_set",
        "capacity:perception:a1.sense_poses",
        "capacity:validate:a1.diagnose_actuators",
    )
    assert atomic_capacity_iris("arm-jaw")[1] == "capacity:mechanism:a2.jaw_set"
    assert atomic_capacity_iris("conveyor") == (
        "capacity:mechanism:conv.run", "capacity:mechanism:conv.stop")
    assert atomic_capacity_iris("manager") == ()


def test_register_and_invoke_arm():
    kl, cl = _cl()
    sess = _DuckSession("arm1")
    iris = register_embodied_capacities(
        cl, device_type="arm-suction", body=_FakeBody(), kl=kl, session=sess,
        device_id="arm1")
    assert set(iris) == set(atomic_capacity_iris("arm-suction"))
    # idempotent re-register (upsert) — no raise
    register_embodied_capacities(cl, device_type="arm-suction", body=_FakeBody(),
                                 kl=kl, session=sess, device_id="arm1")

    r = cl.invoke("capacity:mechanism:a1.move_to",
                  {DS_POSE_TARGET: {"named": "rest"}}, session=sess)
    assert r.success and r.outputs[DS_MOTION_DONE]["status"] == "done"

    r = cl.invoke("capacity:mechanism:a1.suction_set",
                  {DS_GRIP_CMD: {"engage": True}}, session=sess)
    assert r.success and r.outputs[DS_GRIP_STATE]["attached"] is True
    assert r.outputs[DS_GRIP_STATE]["kind"] == "suction"

    r = cl.invoke("capacity:perception:a1.sense_poses",
                  {DS_DIAG_REQUEST: {}}, session=sess)
    assert r.success and "box1" in r.outputs[DS_WORLD_FACT]["poses"]


def test_diagnose_records_local_gap():
    kl, cl = _cl()
    sess = _DuckSession("arm1")
    register_embodied_capacities(cl, device_type="arm-suction",
                                 body=_FakeBody(frozen=["a1_joint3"]),
                                 kl=kl, session=sess, device_id="arm1")
    r = cl.invoke("capacity:validate:a1.diagnose_actuators",
                  {DS_DIAG_REQUEST: {}}, session=sess)
    rep = r.outputs[DS_DIAG_REPORT]
    assert rep["healthy"] is False and rep["frozen_joints"] == ["a1_joint3"]
    assert rep["gap_recorded"] is True
    g = MetagraphView(kl.local_metagraph("arm1")).graphs_by_role("capacity-state")[0]
    assert "gap:arm1:actuators" in g.nodes  # PB-K: Local, no Global write


def test_diagnose_healthy_no_gap():
    kl, cl = _cl()
    sess = _DuckSession("arm2")
    register_embodied_capacities(cl, device_type="arm-jaw", body=_FakeBody(),
                                 kl=kl, session=sess, device_id="arm2")
    r = cl.invoke("capacity:validate:a2.diagnose_actuators",
                  {DS_DIAG_REQUEST: {}}, session=sess)
    rep = r.outputs[DS_DIAG_REPORT]
    assert rep["healthy"] is True and rep["gap_recorded"] is False


def test_conveyor_and_manager_noop():
    kl, cl = _cl()
    sess = _DuckSession("conv")
    register_embodied_capacities(cl, device_type="conveyor", body=_FakeBody(),
                                 kl=kl, session=sess, device_id="conv")
    r = cl.invoke("capacity:mechanism:conv.run",
                  {DS_BELT_CMD: {"direction": 1, "distance": 0.3}}, session=sess)
    assert r.success and abs(r.outputs[DS_BELT_DONE]["displaced"] - 0.3) < 1e-9
    r = cl.invoke("capacity:mechanism:conv.stop", {DS_BELT_CMD: {}}, session=sess)
    assert r.success and r.outputs[DS_BELT_DONE]["action"] == "stop"
    assert register_embodied_capacities(cl, device_type="manager", body=None,
                                        device_id="mgr") == []


# ── core: subset checklist (PB-LL) ────────────────────────────────────
def test_atomic_checklist_pass_and_fail():
    spec = _spec()
    bodies = ["a1_link0", "a1_link1", "a1_link6", "a1_attachment"]
    clean = [[[0.0 + 0.01 * f, 0.5, 1.5, 1, 0, 0, 0] for _ in bodies] for f in range(10)]
    assert atomic_checklist(clean, bodies, 1, spec).ok
    # conveyor intrusion
    dirty = [[[0.0, 0.4, 0.5, 1, 0, 0, 0] for _ in bodies] for _ in range(10)]
    v = atomic_checklist(dirty, bodies, 1, spec)
    assert not v.ok and "conveyor" in v.reason
    # jerk spike (IK branch-flip)
    jerky = [[[0.0, 0.5, 1.5, 1, 0, 0, 0] for _ in bodies] for _ in range(5)]
    jerky[2][0][0] = 1.0
    assert not atomic_checklist(jerky, bodies, 1, spec).ok


# ── core: live-motion policy (PB-F) ───────────────────────────────────
def test_live_motion_hit_miss_dontknow():
    cache = TrajectoryCache()
    key = make_key(1, "move_to", "rest")
    traj = Trajectory(qpos=[[0] * 7, [0] * 7], body=[[[0, 0, 0, 1, 0, 0, 0]]])
    ok_v = type("V", (), {"ok": True, "reason": "PASS", "checks": {}})()
    bad_v = type("V", (), {"ok": False, "reason": "rack upper-link", "checks": {}})()
    played = []

    o = run_motion(cache, key, lambda: traj, played.append, lambda t: ok_v)
    assert o.ok and not o.cache_hit and o.frames_n == 2 and len(cache) == 1

    o2 = run_motion(cache, key, lambda: pytest.fail("regenerated on hit"),
                    played.append, lambda t: ok_v)
    assert o2.ok and o2.cache_hit

    o3 = run_motion(cache, make_key(1, "move_to", "bad"), lambda: traj,
                    played.append, lambda t: bad_v)
    assert (not o3.ok) and o3.status == "dont_know" and "unsafe motion" in o3.reason

    o4 = run_motion(cache, make_key(1, "move_to", "boom"),
                    lambda: (_ for _ in ()).throw(RuntimeError("ik diverged")),
                    played.append, lambda t: ok_v)
    assert (not o4.ok) and "generation failed" in o4.reason


# ── core: pose projection (DM-4 interface, §16) ───────────────────────
def test_pose_frame_projection():
    from robot_demo.backend.pose_frame import project_pose, Affine2D
    bodies = ["box1", "sheet1", "a1_suction", "a2g_base", "a1_link0", "leg_x"]
    frame = [[0.7, -0.6, 0.5, 1, 0, 0, 0], [-1.1, -0.6, 0.6, 1, 0, 0, 0],
             [-0.7, -0.7, 0.9, 1, 0, 0, 0], [0.7, -0.62, 0.9, 1, 0, 0, 0],
             [0.0, 0.0, 0.2, 1, 0, 0, 0], [9, 9, 9, 1, 0, 0, 0]]
    p = project_pose(frame, bodies)
    assert p["items"]["box1"] == [0.7, 0.5]          # front elevation (x,z)
    assert p["eff"]["a1"] == [-0.7, 0.9]
    assert p["bodies"]["box1"][:3] == [0.7, -0.6, 0.5]
    assert "leg_x" not in p["bodies"]
    p2 = project_pose(frame, bodies, affine=Affine2D(ax=100, bx=5, az=-100, bz=2))
    assert p2["items"]["box1"] == [75.0, -48.0]


# ── core: bootstrap body-guard skip (PB-TT) ───────────────────────────
def test_bootstrap_body_guard_skips_without_mujoco(monkeypatch):
    from robot_demo.backend import bootstrap as B
    monkeypatch.setenv("DEMO_BODY", "0")
    assert B._maybe_build_bodies() is None  # explicit opt-out
    monkeypatch.delenv("DEMO_BODY", raising=False)
    monkeypatch.setenv("DEMO_BOOTSTRAP_ONLY", "1")
    assert B._maybe_build_bodies() is None  # MuJoCo kept out of the DM-1/DM-2 spine


def test_pure_modules_import():
    # mirrors the DM-2 import sentinel: every MuJoCo-free module imports so a
    # missing top-level import fails the sandbox suite, not just the gate.
    import robot_demo.backend.capacities  # noqa: F401
    import robot_demo.backend.motion_cache  # noqa: F401
    import robot_demo.backend.motion_checklist  # noqa: F401
    import robot_demo.backend.live_motion  # noqa: F401
    import robot_demo.backend.pose_frame  # noqa: F401


# ── integration: the live sim (MuJoCo host only) ──────────────────────
@pytest.mark.integration
def test_live_atomic_moves_sim():
    pytest.importorskip("mujoco")
    from robot_demo.backend.body_adapter import build_body_runtime
    engine, handles = build_body_runtime()
    try:
        h = handles["arm1"]
        before = engine.arm_qpos(1)
        out = h.move_to({"named": "home"})       # cache MISS → gen → checklist → play
        assert out.ok and out.status == "done" and not out.cache_hit
        after = engine.arm_qpos(1)
        assert any(abs(a - b) > 1e-4 for a, b in zip(before, after))  # moved
        out2 = h.move_to({"named": "home"})      # cache HIT
        assert out2.ok and out2.cache_hit
    finally:
        engine.stop()


@pytest.mark.integration
def test_fault_injection_detected():
    pytest.importorskip("mujoco")
    from robot_demo.backend.body_adapter import build_body_runtime
    engine, handles = build_body_runtime()
    try:
        engine.freeze_joint(1, 2)                # freeze a1 joint index 2
        report = handles["arm1"].diagnose()
        assert "a1_joint3" in report["frozen_joints"]  # 1-indexed name
        engine.clear_freezes(1)
        assert handles["arm1"].diagnose()["frozen_joints"] == []
    finally:
        engine.stop()


@pytest.mark.integration
def test_belt_sweeps():
    pytest.importorskip("mujoco")
    from robot_demo.backend.body_adapter import build_body_runtime
    engine, handles = build_body_runtime()
    try:
        out = handles["conv"].run_belt(1, 0.2)
        assert abs(out["displaced"] - 0.2) < 1e-9
    finally:
        engine.stop()
