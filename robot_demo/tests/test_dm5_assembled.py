"""DM-5 — ◆ assembled pick / place_at_cell / stage_at composition + registration.

MuJoCo-free: the composition logic is exercised with a fake ``BodyHandle`` that
records the ⬡ atomic call sequence; registration is checked against a real
``CapacityLayer`` (the robot.* DataStates installed). The real cartesian motion
is Linux-gated (``dm5_check``).
"""

from __future__ import annotations

from typing import List

from robot_demo.backend.assembled import (
    assembled_capacity_names,
    make_pick_impl,
    make_place_impl,
    make_stage_impl,
    register_assembled_capacities,
)
from robot_demo.backend.brain import build_brain_stack
from robot_demo.backend.capacities import (
    DS_BELT_CMD,
    DS_MOTION_DONE,
    DS_POSE_TARGET,
)
from robot_demo.backend.installers import install_core_datastates
from robot_demo.backend.profiles import DEVICE_PROFILES


class _FakeBody:
    """Records the atomic sequence; configurable grasp/reach outcomes."""

    def __init__(self, grasp=True, reach_ok=True):
        self.grasp = grasp
        self.reach_ok = reach_ok
        self.calls: List[tuple] = []

    def move_to(self, spec):
        self.calls.append(("move_to", spec.get("phase"), spec.get("item") or spec.get("cell")))
        return {"ok": self.reach_ok, "status": "done" if self.reach_ok else "dont_know"}

    def set_grip(self, engage, obj=None):
        self.calls.append(("set_grip", engage, obj))
        return {"attached": bool(engage and self.grasp)}

    def run_belt(self, direction, distance):
        self.calls.append(("run_belt", direction, distance))
        return {"displaced": direction * distance}


class _DuckSession:
    def __init__(self, u):
        self.user_id = u
        self.username = u

    @property
    def caps(self):
        return set()


# ── composition: the ◆ really sequences the ⬡ atomics ─────────────────────
def test_pick_sequences_approach_grip_lift():
    body = _FakeBody()
    out = make_pick_impl(body)(**{DS_POSE_TARGET: {"item": "box1"}})
    payload = out[DS_MOTION_DONE]
    assert payload["ok"] and payload["assembled"] == "pick" and payload["attached"]
    phases = [c for c in body.calls]
    assert phases[0] == ("move_to", "approach", "box1")
    assert phases[1] == ("set_grip", True, "box1")
    assert phases[2] == ("move_to", "lift", "box1")


def test_pick_honest_dont_know_when_grasp_fails():
    body = _FakeBody(grasp=False)
    out = make_pick_impl(body)(**{DS_POSE_TARGET: {"item": "tube1"}})
    payload = out[DS_MOTION_DONE]
    assert not payload["ok"] and payload["status"] == "dont_know"
    assert "grasp" in payload["reason"]
    # never lifts on a failed grasp
    assert ("move_to", "lift", "tube1") not in body.calls


def test_pick_dont_know_when_approach_unsafe():
    body = _FakeBody(reach_ok=False)
    out = make_pick_impl(body)(**{DS_POSE_TARGET: {"item": "box1"}})
    payload = out[DS_MOTION_DONE]
    assert not payload["ok"] and "approach" in payload["reason"]
    # never grips if it can't reach
    assert not any(c[0] == "set_grip" for c in body.calls)


def test_place_sequences_carry_release_retract():
    body = _FakeBody()
    out = make_place_impl(body)(**{DS_POSE_TARGET: {"item": "box1", "cell": "r1c1"}})
    payload = out[DS_MOTION_DONE]
    assert payload["ok"] and payload["assembled"] == "place_at_cell"
    assert payload["cell"] == "r1c1"
    assert [c[0] for c in body.calls] == ["move_to", "set_grip", "move_to"]
    assert body.calls[1] == ("set_grip", False, "box1")  # release


def test_stage_runs_belt():
    body = _FakeBody()
    out = make_stage_impl(body)(**{DS_BELT_CMD: {"direction": 1, "distance": 0.4}})
    assert out  # DS_BELT_DONE payload
    assert ("run_belt", 1, 0.4) in body.calls


# ── registration against a real CapacityLayer ─────────────────────────────
def test_register_assembled_into_arm_cl():
    arm = build_brain_stack(DEVICE_PROFILES["arm1"], _DuckSession("arm1"))
    install_core_datastates(arm.cl)
    body = _FakeBody()
    ids = register_assembled_capacities(
        arm.cl, device_type="arm-suction", body=body, device_id="arm1"
    )
    assert len(ids) == 2  # a1.pick + a1.place_at_cell
    assert assembled_capacity_names("arm-suction") == ("a1.pick", "a1.place_at_cell")
    assert assembled_capacity_names("conveyor") == ("conv.stage_at",)
    # the registered ◆ capacity actually runs (composes the fake atomics)
    from mindsos_capacity.identifiers import capacity_iri
    res = arm.cl.invoke(
        capacity_iri("mechanism", "a1.pick"),
        {DS_POSE_TARGET: {"item": "box1"}}, session=None,
    )
    assert res.success and res.outputs[DS_MOTION_DONE]["assembled"] == "pick"
    arm.il.stop()
