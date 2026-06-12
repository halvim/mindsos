"""DM-4 — gate-flow wiring (plan §2.1/§2.2; design-log PB-WW/EEE/FFF).

Ties the proven pieces together into the live DM-4 flow and narrates it onto
the UI:

    place_order (WS)  → mgr.run_lifecycle
      phase-1 map override   : decide (arm, target)   → encode in task_pattern_iri
      phase-2 derive override: comms.dispatch ──bus──▶ arm.run_lifecycle
                                                         phase-2 derive: run_atomic(move_to)
                                                       ◀── comms.report ──
      → ack ; consolidate ; narrate

Backend ids are **device ids** (``mgr``/``arm1``/``arm2``/``conv``) on the
bus and brains; only the frame layer (:class:`DemoEvents`) aliases to the
contract ids (``a1``/``a2``). The arm's atomic is injected (``run_atomic``)
so this module is MuJoCo-free and sandbox-testable — the live runtime injects
``arm.cl.invoke(a{n}.move_to, …)``; the sandbox injects a stub.

Promotes the inline overrides validated in ``test_dm4_comms`` into reusable
installers, now emitting ``state``/``message`` frames at each beat.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from mindsos_capacity.builtins.phase1_v0 import DS_STRUCTURED_INPUT, DS_MAPPING
from mindsos_capacity.builtins.planning_v0 import DS_PLAN, DS_MAPPING_RESULT
from mindsos_intelligence.phase_1 import MAP_IRI, PROCESS_IRI
from mindsos_intelligence.plan_construction import DERIVE_PLAN_IRI

from .brain import run_task
from .comms import (
    DISPATCH_IRI,
    DS_DISPATCH_ACK,
    DS_DISPATCH_CMD,
    KIND_DISPATCH,
    decode_target,
    encode_target,
    install_override,
    make_dispatch_handler,
    register_comms_capacities,
)
from .frames import DemoEvents
from .installers import install_core_datastates
from .pose_frame import project_pose

#: run_atomic(brain, target) -> outcome dict. Live = move_to invoke; stub in tests.
RunAtomic = Callable[[Any, str], dict]


#: bounded base-yaw delta from the live pose — the DM-3-verified smooth,
#: conveyor-clear move that works for both arms (dm3_check ``ready_delta``).
_READY_DELTA = (0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def _stub_run_atomic(brain: Any, target: str) -> dict:
    """No-body fallback (sandbox / DEMO_BODY=0): record + succeed so the flow
    still completes and reports."""
    return {"status": "succeeded", "note": "stub (no body)", "target": target}


def make_live_run_atomic(sim_engine: Any) -> "RunAtomic":
    """The live atomic: invoke the arm's shipped ``move_to`` capacity with the
    DM-3-verified ``qpos`` spec (current pose + bounded base-yaw delta), over
    the brain's own CL. Returns the outcome the report carries."""
    from mindsos_capacity.identifiers import capacity_iri

    def run_atomic(brain: Any, target: str) -> dict:
        arm = 1 if brain.device_id == "arm1" else 2
        move_iri = capacity_iri("mechanism", f"a{arm}.move_to")
        try:
            from .capacities import DS_MOTION_DONE, DS_POSE_TARGET
            qpos = [v + d for v, d in zip(sim_engine.arm_qpos(arm), _READY_DELTA)]
            res = brain.cl.invoke(
                move_iri,
                {DS_POSE_TARGET: {"qpos": qpos, "key": f"dm4-{target}"}},
                session=None,
            )
            if res.success:
                out = res.outputs.get(DS_MOTION_DONE) or {}
                ok = out.get("ok", True)
                return {"status": "succeeded" if ok else "dont_know", "motion": out}
            return {"status": "dont_know", "reason": repr(res.error)}
        except Exception as exc:  # noqa
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    return run_atomic


# ── per-brain comms wiring ────────────────────────────────────────────
def wire_brain_comms(brain: Any, bus: Any) -> Tuple[str, ...]:
    """Register the brain's bus endpoint + the 4 comms.* capacities. The
    robot.* DataStates must already be installed (DM-2 bundle / direct)."""
    bus.register_endpoint(brain.device_id)
    return register_comms_capacities(brain.cl, bus, brain.device_id)


# ── Manager overrides ─────────────────────────────────────────────────
def install_manager_flow(
    mgr: Any, bus: Any, events: DemoEvents,
    *, decide: Callable[[dict], Tuple[str, str]],
) -> None:
    """Override mgr phase-1 map (decide arm+target → task_pattern_iri) and
    phase-2 derive (dispatch over the bus, narrate)."""

    def mgr_map(context=None, **inputs):
        structured = inputs.get(DS_STRUCTURED_INPUT) or {}
        order = structured.get("order") if isinstance(structured, dict) else structured
        dst, target = decide({"order": order})
        return {DS_MAPPING: {"task_pattern_iri": encode_target(dst, target),
                             "mapping_confidence": 1.0}}

    def mgr_derive(context=None, **inputs):
        mr = inputs.get(DS_MAPPING_RESULT) or {}
        dst, target = decode_target(mr.get("task_pattern_iri", ""))
        # behavior-level text only (policy B / IP sanitization) — no IRIs,
        # no API/type names. The guard test enforces this.
        events.state({"mgr": {"intent": "Allocate + assign",
                              "decision": f"assign move ({target}) → {dst}",
                              "chain": 3, "active": True}},
                     title="Assign task", narr=f"Manager assigns the move to {dst}.")
        events.message("mgr", dst, f"move to {target}")
        cmd = {"dst": dst, "capacity": "move_to", "target": target,
               "task_id": "order-sub"}
        res = mgr.cl.invoke(DISPATCH_IRI, {DS_DISPATCH_CMD: cmd}, session=None)
        ack = res.outputs.get(DS_DISPATCH_ACK) if res.success else None
        status = (ack or {}).get("status", "dont_know")
        # state-then-message (canonical — groups the report with this beat).
        events.state({"mgr": {"intent": "Order complete",
                              "decision": f"{dst} reported {status}",
                              "chain": 5, "active": False}},
                     title="Reported", narr="Manager received the arm's report.")
        events.message(dst, "mgr", f"reported: {status}")
        return {DS_PLAN: {"dispatched": cmd, "ack": ack}}

    install_override(mgr.cl, MAP_IRI, mgr_map)
    install_override(mgr.cl, DERIVE_PLAN_IRI, mgr_derive)


# ── Arm overrides + dispatch handler ──────────────────────────────────
def install_arm_flow(
    arm: Any, bus: Any, events: DemoEvents, *, run_atomic: RunAtomic,
) -> None:
    """Override arm phase-1 (identity + encode the dispatched target) and
    phase-2 derive (run the atomic, narrate), and set its bus dispatch
    handler so the work runs inside the arm's own lifecycle (the gate)."""

    def arm_process(context=None, **inputs):
        return {DS_STRUCTURED_INPUT: next(iter(inputs.values()), None)}

    def arm_map(context=None, **inputs):
        structured = inputs.get(DS_STRUCTURED_INPUT) or {}
        cmd = structured.get("order") if isinstance(structured, dict) else {}
        target = (cmd or {}).get("target", "home")
        return {DS_MAPPING: {"task_pattern_iri": encode_target(arm.device_id, target),
                             "mapping_confidence": 1.0}}

    def arm_derive(context=None, **inputs):
        mr = inputs.get(DS_MAPPING_RESULT) or {}
        _dst, target = decode_target(mr.get("task_pattern_iri", ""))
        events.state({arm.device_id: {"intent": f"Execute move ({target})",
                                      "decision": "running…", "chain": 4,
                                      "active": True}})
        outcome = run_atomic(arm, target)
        events.state({arm.device_id: {"intent": f"Execute move ({target})",
                                      "decision": f"move {target} "
                                      f"{'✓' if outcome.get('status') == 'succeeded' else '✗'}",
                                      "chain": 5, "active": True}})
        return {DS_PLAN: {"executed": target, "outcome": outcome}}

    install_override(arm.cl, PROCESS_IRI, arm_process)
    install_override(arm.cl, MAP_IRI, arm_map)
    install_override(arm.cl, DERIVE_PLAN_IRI, arm_derive)

    bus.set_handler(
        arm.device_id, KIND_DISPATCH,
        make_dispatch_handler(bus, arm, build_task_input=lambda cmd: {"order": cmd}),
    )


# ── pose stream (sim → UI) ────────────────────────────────────────────
def wire_pose_stream(sim_engine: Any, events: DemoEvents) -> None:
    """Subscribe the SimEngine pose stream → projected ``pose`` frames.

    The callback runs on the sim-clock thread but only projects (cheap) and
    calls ``events.pose`` → ``hub.publish`` → ``call_soon_threadsafe`` — the
    socket send happens on the WS loop, never the sim thread (PB-ZZ)."""
    def on_frame(frame, bodies):
        proj = project_pose(frame, bodies)
        events.pose(items=proj["items"], eff=proj["eff"])
    sim_engine.subscribe(on_frame)


# ── top-level wiring + command handler ────────────────────────────────
def wire_demo(
    brains: Dict[str, Any],
    bus: Any,
    events: DemoEvents,
    *,
    run_atomic: Optional[RunAtomic] = None,
    decide: Optional[Callable[[dict], Tuple[str, str]]] = None,
    install_datastates: bool = False,
) -> "Callable[[str, dict], None]":
    """Wire the whole demo and return the WS command handler.

    ``install_datastates`` is for tests/sandbox where the DM-2 bundle install
    hasn't run; the live bootstrap already installed the robot.* DataStates.
    ``decide`` maps an order → (arm device-id, target); default = fixed
    arm1/home (thin slice; DM-5 does real allocation)."""
    run_atomic = run_atomic or _stub_run_atomic
    decide = decide or (lambda order: ("arm1", "home"))

    # Always ensure the robot.* DataStates (idempotent). On a Falkor RELOAD
    # boot, install_skill no-ops (digest match) so the bundle's L3 installer
    # does NOT re-register them into the fresh CapacityLayer (F9) — and comms.*
    # registration needs them. install_datastates is retained for back-compat
    # but the ensure now runs unconditionally.
    for brain in brains.values():
        install_core_datastates(brain.cl)
        wire_brain_comms(brain, bus)

    for did, brain in brains.items():
        if did == "mgr":
            install_manager_flow(brain, bus, events, decide=decide)
        elif did in ("arm1", "arm2"):
            install_arm_flow(brain, bus, events, run_atomic=run_atomic)

    mgr = brains["mgr"]

    def on_command(name: str, args: dict) -> None:
        if name == "place_order":
            # state-then-message (canonical — groups the order with this beat).
            events.state({"mgr": {"intent": "Interpret order",
                                  "decision": "understand the request",
                                  "chain": 1, "active": True}},
                         title="Order placed", narr="User submitted an order.")
            events.message("user", "mgr", "placed an order")
            run_task(mgr, {"order": args}, task_id="order")
        elif name == "reset":
            events.reset()
        # play/pause/step are mock-playback concepts; live runs on real orders.

    return on_command


__all__ = [
    "wire_demo", "wire_brain_comms", "install_manager_flow", "install_arm_flow",
    "wire_pose_stream", "make_live_run_atomic", "RunAtomic",
]
