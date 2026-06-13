"""DM-5 — the ◆ assembled L3 capacities (``pick`` / ``place_at_cell`` /
``stage_at``), composing the DM-3 ⬡ atomics over the live shared sim.

**PB-1c (design-log §23):** the cinematic offline ``combo_*`` clips can't be
live capabilities (own-``Cell``, ~45 s IK, ``_save`` JSON, per-cell-tuned, and
the ``SimEngine`` slot model has no mid-trajectory attach channel). So a ◆
capability here is a **real composite of the proven ⬡ atomics** — real grasp,
real cartesian reach, real release — graph-honest (``find_pipeline`` sees the
composition) and live, if plainer on camera than the 46 authored clips. The
authored-clip replay is a later polish, not DM-5.

Split (mirrors DM-3 PB-TT):

* This module is **MuJoCo-free**: it composes a ``BodyHandle`` duck and is
  sandbox-tested with a fake body that records the atomic call sequence.
* The real cartesian reach (item/cell IK + grasp calibration) lives in
  :class:`~robot_demo.backend.sim_engine.SimEngine` /
  :class:`~robot_demo.backend.body_adapter.BodyHandle` and is **Linux-gated**.

BodyHandle duck contract this module relies on:
  * ``move_to(spec) -> MotionOutcome``      (``spec`` may carry ``item``/``cell``)
  * ``set_grip(engage, obj=…) -> dict``
  * ``run_belt(direction, distance) -> dict``
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple

from mindsos_capacity import Capacity

from .capacities import (
    CAT_MECHANISM,
    DS_BELT_CMD,
    DS_BELT_DONE,
    DS_MOTION_DONE,
    DS_POSE_TARGET,
    _as_payload,
)


def _ok(outcome: Any) -> bool:
    if isinstance(outcome, dict):
        return bool(outcome.get("ok", True))
    return bool(getattr(outcome, "ok", True))


# ── ◆ pick = approach → grip-engage → lift (compose the ⬡ atomics) ────────
def make_pick_impl(body: Any) -> Callable[..., dict]:
    """``pick(item)`` — reach the item's grasp pose, close the gripper on a
    genuine contact (attach-on-valid-contact), lift clear. A failed grasp or an
    unsafe reach surfaces as an honest ``status:"dont_know"`` (the atomic
    ``move_to`` already returns that on a checklist-failing live miss)."""

    def impl(context=None, **inputs):
        spec = inputs.get(DS_POSE_TARGET) or {}
        item = spec.get("item")
        steps: List[dict] = []

        approach = body.move_to({"item": item, "phase": "approach"})
        steps.append({"step": "approach", **_as_payload(approach)})
        if not _ok(approach):
            return {DS_MOTION_DONE: _assembled_payload(False, "pick", steps,
                                                       reason="no safe approach")}

        grip = body.set_grip(True, obj=item)
        attached = bool(grip.get("attached")) if isinstance(grip, dict) else bool(grip)
        steps.append({"step": "grip", "attached": attached})
        if not attached:
            return {DS_MOTION_DONE: _assembled_payload(False, "pick", steps,
                                                       reason="grasp did not engage")}

        lift = body.move_to({"item": item, "phase": "lift"})
        steps.append({"step": "lift", **_as_payload(lift)})
        return {DS_MOTION_DONE: _assembled_payload(_ok(lift), "pick", steps,
                                                   item=item, attached=True)}

    return impl


# ── ◆ place_at_cell = reach-cell → release → retract ──────────────────────
def make_place_impl(body: Any) -> Callable[..., dict]:
    """``place_at_cell(item, cell)`` — carry the held item to the shelf cell,
    release on seat, retract clear."""

    def impl(context=None, **inputs):
        spec = inputs.get(DS_POSE_TARGET) or {}
        item, cell = spec.get("item"), spec.get("cell")
        steps: List[dict] = []

        reach = body.move_to({"cell": cell, "item": item, "phase": "seat"})
        steps.append({"step": "carry", **_as_payload(reach)})
        if not _ok(reach):
            return {DS_MOTION_DONE: _assembled_payload(False, "place_at_cell", steps,
                                                       reason="no safe path to cell")}

        rel = body.set_grip(False, obj=item)
        released = not (rel.get("attached") if isinstance(rel, dict) else rel)
        steps.append({"step": "release", "released": released})

        retract = body.move_to({"named": "home", "phase": "retract"})
        steps.append({"step": "retract", **_as_payload(retract)})
        return {DS_MOTION_DONE: _assembled_payload(_ok(retract), "place_at_cell",
                                                   steps, item=item, cell=cell)}

    return impl


# ── ◆ stage_at = command the belt to a staging position ───────────────────
def make_stage_impl(body: Any) -> Callable[..., dict]:
    """``stage_at(direction, distance)`` — the conveyor ◆: move the belt to the
    staging position (the proven kinematic sweep), the cross-gap bridge. The
    carrier-box cooperation Plan over this is the DM-6 headline skill."""

    def impl(context=None, **inputs):
        cmd = inputs.get(DS_BELT_CMD) or {}
        direction = int(cmd.get("direction", 1))
        distance = float(cmd.get("distance", 0.0))
        out = body.run_belt(direction, distance)
        payload = dict(out) if isinstance(out, dict) else {"ok": bool(out)}
        payload.update({"action": "stage_at", "assembled": True})
        return {DS_BELT_DONE: payload}

    return impl


def _assembled_payload(ok: bool, name: str, steps: List[dict], *,
                       reason: str = "", **extra) -> dict:
    return {
        "ok": ok,
        "status": "done" if ok else "dont_know",
        "assembled": name,
        "reason": reason if not ok else "",
        "steps": steps,
        **extra,
    }


# ── registration (◆ alongside the ⬡ atomics; profile-declared IRIs) ───────
_AssembledSpec = Tuple[str, str, Tuple[str, ...], Tuple[str, ...], Callable[..., dict]]


def _specs_for(device_type: str, body: Any) -> List[_AssembledSpec]:
    if device_type == "arm-suction":
        n = 1
    elif device_type == "arm-jaw":
        n = 2
    elif device_type == "conveyor":
        return [("conv.stage_at", CAT_MECHANISM, (DS_BELT_CMD,), (DS_BELT_DONE,),
                 make_stage_impl(body))]
    else:
        return []
    return [
        (f"a{n}.pick", CAT_MECHANISM, (DS_POSE_TARGET,), (DS_MOTION_DONE,),
         make_pick_impl(body)),
        (f"a{n}.place_at_cell", CAT_MECHANISM, (DS_POSE_TARGET,), (DS_MOTION_DONE,),
         make_place_impl(body)),
    ]


def assembled_capacity_names(device_type: str) -> Tuple[str, ...]:
    return tuple(name for name, *_ in _specs_for(device_type, body=None))


def register_assembled_capacities(
    cl: Any, *, device_type: str, body: Any, device_id: str = ""
) -> List[str]:
    """Register the device's ◆ assembled capacities into its own CL Global
    (``session=None``, like the ⬡ atomics — that's where the ``robot.*``
    DataStates live). Returns the registered node ids. No-op for the manager."""
    registered: List[str] = []
    for name, category, inputs, outputs, impl in _specs_for(device_type, body):
        decl = Capacity(
            name=name,
            category=category,
            inputs=inputs,
            outputs=outputs,
            implementation=impl,
            description=f"DM-5 ◆ assembled {name} ({device_id}).",
        )
        node = cl.register_capacity(decl, session=None, if_exists="upsert")
        registered.append(node.node_id)
    return registered


__all__ = [
    "make_pick_impl",
    "make_place_impl",
    "make_stage_impl",
    "register_assembled_capacities",
    "assembled_capacity_names",
]
