"""DM-3 — atomic ⬡ L3 capacities, per embodied brain (plan §4.1-§4.3).

The ⬡ atomic primitives only — ``move_to``, ``suction_set``/``jaw_set``,
``sense_poses``, ``diagnose_actuators`` (arms); ``conv.run``/``conv.stop``
(conveyor). The ◆ assembled (``pick``/``place_at_cell``/``stage_at``) and ★
learned rows are DM-5/DM-6 and are NOT registered here (so this roster is
defined locally, not read from ``profile.embodied`` which forward-declares
DM-5 names — design log §15 scope note).

**Closure injection (P-4):** each body closes over its brain's ``BodyHandle``
(the per-brain sim seam). ``BodyHandle`` can't ride a bundle installer, so
registration happens directly per brain in the bootstrap step-6 hook.

**Registration scope (PB-UU):** registered ``session=None`` into the brain's
own CL **Global** — the ``robot.*`` DataStates were installed there by DM-2,
and ``register_capacity`` validates inputs/outputs against the target
metagraph. Per-brain CLs ⇒ Global-of-its-own-CL is private. ``register_
capacity`` emits the PRODUCES/CONSUMES IntergraphEdges from inputs/outputs
(ADR-0156) — what makes ``find_pipeline`` + the graph-viz tab honest.

**Families (design log §15):** ``mechanism`` (move/grip/belt — OPTIONAL_
RETURN), ``perception`` (sense — DATASTATE_MARKER), ``validate`` (diagnose —
VALIDATION_RESULT). Not in ``FUNCTIONAL_CATEGORIES`` but accepted by
``ensure_category_graph`` (the ``text``/``dream`` precedent) and resolved by
``family_rule_for`` by category.

MuJoCo-free (PB-TT): ``body`` is a duck (the real one is
:mod:`body_adapter`, MuJoCo); ``make_writeable`` is the domain stack. So
this module + ``register_embodied_capacities`` are sandbox-testable with a
fake body.

BodyHandle duck contract (see :mod:`body_adapter`):
  * ``move_to(spec: dict) -> MotionOutcome`` (cache→gen→checklist→play|dont_know)
  * ``set_grip(engage: bool) -> dict``  (attach-on-valid-contact toggle)
  * ``sense_poses() -> dict``           (sim body poses → world facts)
  * ``diagnose() -> dict``              (commanded-vs-actual per joint)
  * ``run_belt(direction: int, distance: float) -> dict``
  * ``stop_belt() -> dict``
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple

from mindsos_capacity import Capacity
from mindsos_capacity.context import make_writeable
from mindsos_capacity.identifiers import datastate_iri

from .seeds import ROLE_CAPACITY_STATE, SNAPSHOT_TYPE

# ── §4.0 DataState IRIs the atomics consume/produce (DM-2 registered) ──
DS_POSE_TARGET = datastate_iri("robot.pose_target")
DS_MOTION_DONE = datastate_iri("robot.motion_done")
DS_GRIP_CMD = datastate_iri("robot.grip_cmd")
DS_GRIP_STATE = datastate_iri("robot.grip_state")
DS_DIAG_REQUEST = datastate_iri("robot.diag_request")
DS_WORLD_FACT = datastate_iri("robot.world_fact")
DS_DIAG_REPORT = datastate_iri("robot.diag_report")
DS_BELT_CMD = datastate_iri("robot.belt_cmd")
DS_BELT_DONE = datastate_iri("robot.belt_done")

# Family/category keys (resolve the intended dont-know shapes).
CAT_MECHANISM = "mechanism"
CAT_PERCEPTION = "perception"
CAT_VALIDATE = "validate"


def _as_payload(outcome: Any) -> dict:
    """Normalise a BodyHandle MotionOutcome (or dict) into a DataState dict."""
    if isinstance(outcome, dict):
        return outcome
    return {
        "ok": getattr(outcome, "ok", True),
        "status": getattr(outcome, "status", "done"),
        "reason": getattr(outcome, "reason", ""),
        "frames": getattr(outcome, "frames_n", 0),
        "cache_hit": getattr(outcome, "cache_hit", False),
        "checks": getattr(outcome, "checks", {}),
    }


# ── impl factories (closures over the BodyHandle) ─────────────────────

def make_move_impl(body: Any) -> Callable[..., dict]:
    def impl(context=None, **inputs):  # noqa: ANN001 — IRI-keyed kwargs
        spec = inputs.get(DS_POSE_TARGET)
        if spec is None:
            raise ValueError("move_to: missing DS_POSE_TARGET input")
        return {DS_MOTION_DONE: _as_payload(body.move_to(spec))}
    return impl


def make_grip_impl(body: Any, kind: str) -> Callable[..., dict]:
    def impl(context=None, **inputs):
        cmd = inputs.get(DS_GRIP_CMD) or {}
        engage = bool(cmd.get("engage", True))
        out = body.set_grip(engage)
        payload = dict(out) if isinstance(out, dict) else {"attached": bool(out)}
        payload.setdefault("kind", kind)
        payload.setdefault("engage", engage)
        return {DS_GRIP_STATE: payload}
    return impl


def make_sense_impl(body: Any) -> Callable[..., dict]:
    def impl(context=None, **inputs):
        poses = body.sense_poses()
        return {DS_WORLD_FACT: {"poses": poses, "kind": "world_fact"}}
    return impl


def make_diagnose_impl(
    body: Any, *, kl: Optional[Any], session: Optional[Any], device_id: str
) -> Callable[..., dict]:
    """diagnose reads commanded-vs-actual and, on a detected gap, records it
    to the brain's OWN Local capacity-state (PB-K/PB-NN) — via a closure-
    captured ``make_writeable`` (this is a read-body, so ``ctx.writeable`` is
    None; the gap-write must not rely on it)."""
    def impl(context=None, **inputs):
        report = dict(body.diagnose())
        frozen = report.get("frozen_joints") or []
        report["healthy"] = not frozen
        report["gap_recorded"] = False
        if frozen and kl is not None and session is not None:
            report["gap_recorded"] = _record_local_gap(
                kl, session, device_id, frozen, report
            )
        return {DS_DIAG_REPORT: report}
    return impl


def make_belt_impl(body: Any, action: str) -> Callable[..., dict]:
    def impl(context=None, **inputs):
        cmd = inputs.get(DS_BELT_CMD) or {}
        if action == "stop":
            out = body.stop_belt()
        else:
            direction = int(cmd.get("direction", 1))
            distance = float(cmd.get("distance", 0.0))
            out = body.run_belt(direction, distance)
        payload = dict(out) if isinstance(out, dict) else {"ok": bool(out)}
        payload.setdefault("action", action)
        return {DS_BELT_DONE: payload}
    return impl


def _record_local_gap(
    kl: Any, session: Any, device_id: str, frozen: list, report: dict
) -> bool:
    """Write a capacity-gap CapacitySnapshot to the brain's Local (PB-K).

    Local-only ⇒ rides ``make_writeable`` with the brain's own session, no
    ``CAN_WRITE_GLOBAL`` (Phase-48 PB-10). Idempotent by stable node_id.
    Returns True if the gap is recorded (written now or already present).
    """
    writeable = make_writeable(kl, session)
    if writeable is None:
        return False
    graph = writeable(role=ROLE_CAPACITY_STATE, scope="local").graph()
    node_id = f"gap:{device_id}:actuators"
    if node_id in graph.nodes:
        return True
    graph.add_node(
        {
            "snapshot_kind": "capacity_gap",
            "device": device_id,
            "capacity": "diagnose_actuators",
            "frozen_joints": list(frozen),
            "detail": {k: report[k] for k in ("deltas",) if k in report},
        },
        SNAPSHOT_TYPE,
        properties={"snapshot_kind": "capacity_gap", "device": device_id},
        node_id=node_id,
    )
    return True


# ── the atomic roster, per device type ────────────────────────────────

_AtomicSpec = Tuple[str, str, Tuple[str, ...], Tuple[str, ...], Callable[..., dict]]


def _arm_specs(arm: int, grip_name: str, grip_kind: str, body: Any,
               kl, session, device_id) -> List[_AtomicSpec]:
    return [
        (f"a{arm}.move_to", CAT_MECHANISM, (DS_POSE_TARGET,), (DS_MOTION_DONE,),
         make_move_impl(body)),
        (f"a{arm}.{grip_name}", CAT_MECHANISM, (DS_GRIP_CMD,), (DS_GRIP_STATE,),
         make_grip_impl(body, grip_kind)),
        (f"a{arm}.sense_poses", CAT_PERCEPTION, (DS_DIAG_REQUEST,), (DS_WORLD_FACT,),
         make_sense_impl(body)),
        (f"a{arm}.diagnose_actuators", CAT_VALIDATE, (DS_DIAG_REQUEST,),
         (DS_DIAG_REPORT,),
         make_diagnose_impl(body, kl=kl, session=session, device_id=device_id)),
    ]


def _conv_specs(body: Any) -> List[_AtomicSpec]:
    return [
        ("conv.run", CAT_MECHANISM, (DS_BELT_CMD,), (DS_BELT_DONE,),
         make_belt_impl(body, "run")),
        ("conv.stop", CAT_MECHANISM, (DS_BELT_CMD,), (DS_BELT_DONE,),
         make_belt_impl(body, "stop")),
    ]


def _specs_for(device_type: str, body: Any, kl, session, device_id) -> List[_AtomicSpec]:
    if device_type == "arm-suction":
        return _arm_specs(1, "suction_set", "suction", body, kl, session, device_id)
    if device_type == "arm-jaw":
        return _arm_specs(2, "jaw_set", "jaw", body, kl, session, device_id)
    if device_type == "conveyor":
        return _conv_specs(body)
    return []  # manager (no body) — no embodied atomics


def atomic_capacity_iris(device_type: str) -> Tuple[str, ...]:
    """The IRIs DM-3 registers for a device type (tests / roster checks)."""
    specs = _specs_for(device_type, body=None, kl=None, session=None, device_id="?")
    from mindsos_capacity.identifiers import capacity_iri
    return tuple(capacity_iri(cat, name) for name, cat, _i, _o, _impl in specs)


def register_embodied_capacities(
    cl: Any,
    *,
    device_type: str,
    body: Any,
    kl: Optional[Any] = None,
    session: Optional[Any] = None,
    device_id: str = "",
) -> List[str]:
    """Register the device's ⬡ atomic capacities into its own CL.

    ``session=None`` (PB-UU) → the brain's CL Global, where the ``robot.*``
    DataStates live. ``kl``/``session`` are the brain's own (for diagnose's
    Local gap-write closure only — NOT the registration scope). Returns the
    registered IRIs. No-op for the manager (no body).
    """
    specs = _specs_for(device_type, body, kl, session, device_id)
    registered: List[str] = []
    for name, category, inputs, outputs, impl in specs:
        decl = Capacity(
            name=name,
            category=category,
            inputs=inputs,
            outputs=outputs,
            implementation=impl,
            description=f"DM-3 embodied atomic {name} ({device_id}).",
        )
        node = cl.register_capacity(decl, session=None, if_exists="upsert")
        registered.append(node.node_id)
    return registered


__all__ = [
    "register_embodied_capacities",
    "atomic_capacity_iris",
    "DS_POSE_TARGET", "DS_MOTION_DONE", "DS_GRIP_CMD", "DS_GRIP_STATE",
    "DS_DIAG_REQUEST", "DS_WORLD_FACT", "DS_DIAG_REPORT",
    "DS_BELT_CMD", "DS_BELT_DONE",
]
