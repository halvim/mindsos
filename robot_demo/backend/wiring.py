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

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from mindsos_capacity.builtins.phase1_v0 import DS_STRUCTURED_INPUT, DS_MAPPING
from mindsos_capacity.builtins.planning_v0 import DS_PLAN, DS_MAPPING_RESULT
from mindsos_intelligence.phase_1 import MAP_IRI, PROCESS_IRI
from mindsos_intelligence.plan_construction import DERIVE_PLAN_IRI

from .brain import run_task
from .closed_loop import (
    DEFAULT_RECAL_BUDGET,
    TIER_OK,
    TIER_REPORT,
    classify,
    joint_divergence,
)
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
from .frames import BRAIN_ALIAS, DemoEvents, server_status_frame
from .gate import (
    clear_gate_verdict,
    gate_item,
    get_gate_verdict,
    install_arm_gate,
    install_manager_replan,
    set_fault_state,
)
from .installers import install_core_datastates
from .pose_frame import project_pose
from .serializer import KIND_EPISODE_AUDIT, build_episode_audit_snapshot

#: contract brain-id (UI) → device id (backend) — the inverse of BRAIN_ALIAS,
#: for resolving an inbound ``export_state {scope:"a1"}`` to the ``arm1`` brain
#: (design-log PB-10).
_CONTRACT_TO_DEVICE: Dict[str, str] = {c: d for d, c in BRAIN_ALIAS.items()}

#: run_atomic(brain, target) -> outcome dict. Live = move_to invoke; stub in tests.
RunAtomic = Callable[[Any, str], dict]


#: bounded base-yaw delta from the live pose — the DM-3-verified smooth,
#: conveyor-clear move that works for both arms (dm3_check ``ready_delta``).
_READY_DELTA = (0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

#: representative magnitude (rad) reported for a probe-detected frozen actuator
#: that the reach itself didn't exercise — classifies as the major tier.
_MAJOR_DIVERGENCE = 0.30


def _first_item(order: Any) -> Optional[str]:
    """The item of the order's first line (the thing being picked), or None.

    Defensive: a DM-4-style synthetic order with no ``lines`` → None → ungated.
    DM-5's real allocator (one line per dispatch) makes this exact."""
    if isinstance(order, dict):
        lines = order.get("lines")
        if isinstance(lines, list) and lines and isinstance(lines[0], dict):
            return lines[0].get("item")
    return None


def _stub_run_atomic(brain: Any, target: str) -> dict:
    """No-body fallback (sandbox / DEMO_BODY=0): record + succeed so the flow
    still completes and reports."""
    return {"status": "succeeded", "note": "stub (no body)", "target": target}


def _verified_approach(sim_engine: Any, arm: int, item: str,
                       budget: int = DEFAULT_RECAL_BUDGET) -> Tuple[bool, int, float]:
    """DM-6 closed-loop verify→replan-from-current on the approach reach (§25
    PB-T3.2). Command the item's approach pose, verify the achieved joints match
    the commanded ones; a MINOR divergence replans-from-current (re-reach — the
    generator reseeds from the live pose, no backtracking); a MAJOR/persistent
    one is reported. Returns ``(reported, recalibrations, max_divergence)``.

    Verify is joint-space (commanded final qpos vs achieved) — exact, so a clean
    reach reads ~0 and never spuriously recalibrates (gate-validated by
    ``dm6_perturbation_check``)."""
    from .sim_engine import SLOT_A1, SLOT_A2

    slot = SLOT_A1 if arm == 1 else SLOT_A2
    xyz, R = sim_engine.item_grasp_target(arm, item, "approach")
    recal, maxdiv = 0, 0.0
    while True:
        qpos, _ = sim_engine.generate_arm_reach(arm, xyz, R)
        sim_engine.submit(slot, qpos).result(timeout=30)
        div = joint_divergence(list(qpos[-1]), list(sim_engine.arm_qpos(arm)))
        maxdiv = max(maxdiv, div)
        tier = classify(div)
        if tier == TIER_OK:
            # The reach matched — but a dead actuator the reach didn't happen to
            # exercise must still be caught: proactive self-diagnosis (scenario
            # L-3) probes every joint, so a persistent fault can't hide behind a
            # motion that didn't need it. The transient disturb never reaches
            # here (it diverts to recalibrate first, so the probe can't consume
            # the one-shot offset).
            try:
                if sim_engine.probe_actuators(arm).get("frozen_joints"):
                    return (True, recal, max(maxdiv, _MAJOR_DIVERGENCE))
            except Exception:  # noqa — probe is best-effort
                pass
            return (False, recal, maxdiv)
        if tier == TIER_REPORT or recal >= budget:
            return (True, recal, maxdiv)
        recal += 1  # MINOR -> recalibrate: the loop re-reaches from the live pose


def make_live_run_atomic(sim_engine: Any) -> "RunAtomic":
    """The live arm motion (Linux-gated). DM-5: when the dispatch names an item,
    run the ◆ assembled ``pick`` then ``place_at_cell`` (item→cell) over the
    brain's own CL; the item is read from the stashed gate verdict so the
    ``run_atomic(brain, target)`` seam stays back-compat. A no-item dispatch
    (DM-4-style move) falls back to the DM-3-verified base-yaw ``move_to``.

    An honest motion dont-know from any ◆ stage (unsafe reach / failed grasp)
    propagates as ``status:"dont_know"`` — the report the Manager renders."""
    from mindsos_capacity.identifiers import capacity_iri

    def run_atomic(brain: Any, target: str) -> dict:
        arm = 1 if brain.device_id == "arm1" else 2
        from .capacities import DS_MOTION_DONE, DS_POSE_TARGET
        v = get_gate_verdict(brain)
        item = v.item if v is not None else None
        try:
            if item:
                # DM-6 closed-loop: verify the approach reach + recalibrate-from-
                # current on a minor divergence; report (dont-know) on a major /
                # persistent one before committing the grasp (§25 PB-T3.2/T3.3).
                reported, recal, maxdiv = _verified_approach(sim_engine, arm, item)
                set_fault_state(
                    brain, recalibrations=recal, max_divergence=maxdiv,
                    reported=reported,
                    cause=("an actuator did not respond as commanded" if reported
                           else "re-calibrated from the actual position" if recal else ""),
                )
                if reported:
                    # self-diagnosis writes the capacity-gap into the arm's Local
                    # (on-thesis introspective loop) before reporting up (PB-25.13).
                    try:
                        from .capacities import DS_DIAG_REQUEST
                        brain.cl.invoke(
                            capacity_iri("validate", f"a{arm}.diagnose_actuators"),
                            {DS_DIAG_REQUEST: {}}, session=None)
                    except Exception:  # noqa — diagnosis is best-effort
                        pass
                    return {"status": "dont_know", "stage": "verify",
                            "recalibrations": recal}
                pick = brain.cl.invoke(
                    capacity_iri("mechanism", f"a{arm}.pick"),
                    {DS_POSE_TARGET: {"item": item}}, session=None,
                )
                pout = (pick.outputs.get(DS_MOTION_DONE) or {}) if pick.success else {}
                if not pout.get("ok", pick.success):
                    return {"status": "dont_know", "stage": "pick", "motion": pout}
                place = brain.cl.invoke(
                    capacity_iri("mechanism", f"a{arm}.place_at_cell"),
                    {DS_POSE_TARGET: {"item": item, "cell": target}}, session=None,
                )
                qout = (place.outputs.get(DS_MOTION_DONE) or {}) if place.success else {}
                ok = qout.get("ok", place.success)
                return {"status": "succeeded" if ok else "dont_know",
                        "stage": "place_at_cell", "motion": qout}
            # no item → DM-3 base-yaw move (parks the arm; DM-4 parity)
            qpos = [x + d for x, d in zip(sim_engine.arm_qpos(arm), _READY_DELTA)]
            res = brain.cl.invoke(
                capacity_iri("mechanism", f"a{arm}.move_to"),
                {DS_POSE_TARGET: {"qpos": qpos, "key": f"dm5-{target}"}},
                session=None,
            )
            if res.success:
                out = res.outputs.get(DS_MOTION_DONE) or {}
                return {"status": "succeeded" if out.get("ok", True) else "dont_know",
                        "motion": out}
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


# ── Manager reroute (DM-6 PB-T56.4) ───────────────────────────────────
#: the demo's two grippers — which grasp each arm provides.
_ARM_GRASP = {"arm1": "grasp:suction", "arm2": "grasp:jaw"}

#: first-cut belt sweep (m) to re-stage an item from one arm's segment to the
#: other's (the conveyor bridges the disjoint reach). Gate-calibrated (§18).
_RESTAGE_DISTANCE = 0.6


def _alternate_arm(faulted_dst: str, item: Optional[str]) -> Optional[str]:
    """The other arm that can grasp ``item``, or None (→ dead-end). Reuses the
    DM-5 grasp table: box→either, sheet→suction-only, tube→jaw-only."""
    from .feasibility import ITEM_ACCEPTABLE_GRASPS, item_kind

    kind = item_kind(item)
    if kind is None:
        return None
    acceptable = ITEM_ACCEPTABLE_GRASPS.get(kind, frozenset())
    other = "arm2" if faulted_dst == "arm1" else "arm1"
    return other if _ARM_GRASP.get(other) in acceptable else None


# ── Manager overrides ─────────────────────────────────────────────────
def install_manager_flow(
    mgr: Any, bus: Any, events: DemoEvents,
    *, decide: Callable[[dict], Tuple[str, str]], conv: Any = None,
) -> None:
    """Override mgr phase-1 map (decide arm+target → task_pattern_iri) and
    phase-2 derive (dispatch over the bus, narrate). DM-6: on a reported FAULT,
    reroute to the healthy arm (one-shot manager ReplanRecord); a true dead-end
    surfaces an honest dont-know + blame (install_manager_replan)."""

    def mgr_map(context=None, **inputs):
        structured = inputs.get(DS_STRUCTURED_INPUT) or {}
        order = structured.get("order") if isinstance(structured, dict) else structured
        dst, target = decide({"order": order})
        item = _first_item(order)
        return {DS_MAPPING: {"task_pattern_iri": encode_target(dst, target, item),
                             "mapping_confidence": 1.0}}

    def mgr_derive(context=None, **inputs):
        mr = inputs.get(DS_MAPPING_RESULT) or {}
        dst, target, item = decode_target(mr.get("task_pattern_iri", ""))
        # behavior-level text only (policy B / IP sanitization) — no IRIs,
        # no API/type names. The guard test enforces this.
        events.state({"mgr": {"intent": "Allocate + assign",
                              "decision": f"assign move ({target}) → {dst}",
                              "chain": 3, "active": True}},
                     title="Assign task", narr=f"Manager assigns the move to {dst}.")
        events.message("mgr", dst, f"move to {target}")
        # NB: no internal capacity/API name on the cmd — it lands in the arm's
        # task_input, which the Mode-A export serializes (policy B / find_leaks).
        cmd = {"dst": dst, "target": target, "item": item, "task_id": "order-sub"}
        res = mgr.cl.invoke(DISPATCH_IRI, {DS_DISPATCH_CMD: cmd}, session=None)
        ack = res.outputs.get(DS_DISPATCH_ACK) if res.success else None
        status = (ack or {}).get("status", "dont_know")
        cause = ((ack or {}).get("detail") or {}).get("cause")
        last_dst, attempts = dst, [{"dst": dst, "status": status}]

        # DM-6: a reroutable FAULT → re-route to the healthy arm; the manager's
        # one-shot should_replan mints a real ReplanRecord. A wrong-gripper stays
        # terminal (cause != "fault"). No alternate / reroute also fails → honest
        # dead-end (sufficient=False → dont-know + blame).
        if status == "dont_know" and cause == "fault":
            alt = _alternate_arm(dst, item)
            if alt is not None:
                # DM-6 7b: the conveyor bridges the disjoint reach — re-stage the
                # item onto the healthy arm's belt segment before re-dispatching
                # (graph-honest: a real conv.stage_at invoke; sweep is gate-tuned).
                if conv is not None:
                    from mindsos_capacity.identifiers import capacity_iri
                    from .capacities import DS_BELT_CMD
                    events.message("mgr", "conv", f"re-stage toward {alt}")
                    conv.cl.invoke(
                        capacity_iri("mechanism", "conv.stage_at"),
                        {DS_BELT_CMD: {"direction": 1 if alt == "arm2" else -1,
                                       "distance": _RESTAGE_DISTANCE}},
                        session=None,
                    )
                events.message("mgr", alt, f"re-route: move to {target}")
                set_fault_state(mgr, recalibrations=1, reported=False,
                                cause="re-routed to the other arm after a detected fault")
                cmd2 = {"dst": alt, "target": target, "item": item,
                        "task_id": "order-sub-2"}
                res2 = mgr.cl.invoke(DISPATCH_IRI, {DS_DISPATCH_CMD: cmd2}, session=None)
                ack2 = res2.outputs.get(DS_DISPATCH_ACK) if res2.success else None
                status, last_dst = (ack2 or {}).get("status", "dont_know"), alt
                attempts.append({"dst": alt, "status": status})
                if status != "succeeded":  # reroute also failed → dead-end
                    set_fault_state(mgr, recalibrations=1, reported=True,
                                    cause="no available arm could complete the task")
            else:  # nothing else can grasp this item → honest dead-end
                set_fault_state(mgr, recalibrations=0, reported=True,
                                cause="no available arm can handle this item")

        events.state({"mgr": {"intent": "Order complete",
                              "decision": f"reported {status}",
                              "chain": 5, "active": False}},
                     title="Reported", narr="Manager received the arm's report.")
        events.message(last_dst, "mgr", f"reported: {status}")
        return {DS_PLAN: {"attempts": attempts}}

    install_override(mgr.cl, MAP_IRI, mgr_map)
    install_override(mgr.cl, DERIVE_PLAN_IRI, mgr_derive)
    install_manager_replan(mgr)


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
        item = (cmd or {}).get("item")
        # DM-5 embodiment gate: if the dispatch names an item, gate it against
        # this arm's grippers NOW (phase-1 sees the item; the later
        # predicate.sufficient override reads the stashed verdict — PB-NEW). A
        # cmd with no item (DM-4 move) clears the gate → ungated.
        if item:
            gate_item(arm, item)
        else:
            clear_gate_verdict(arm)
        return {DS_MAPPING: {"task_pattern_iri": encode_target(arm.device_id, target, item),
                             "mapping_confidence": 1.0}}

    def arm_derive(context=None, **inputs):
        mr = inputs.get(DS_MAPPING_RESULT) or {}
        _dst, target, item = decode_target(mr.get("task_pattern_iri", ""))
        verdict = get_gate_verdict(arm)
        if verdict is not None and verdict.gated:
            # Honest refusal: do NOT attempt the motion. Surface the GATED badge
            # + a behavior-level decision; the lifecycle's dont-know path (driven
            # by the predicate.sufficient override) produces the real Episode.
            events.state({arm.device_id: {
                "intent": f"Pick {verdict.item_kind or item}",
                "decision": verdict.reason, "chain": 5, "active": True,
                "flags": ["gate"],
                "caps": [["pick", "GATED"]]}})
            return {DS_PLAN: {"gated": True, "item": item, "reason": verdict.reason}}
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
    sim_engine: Optional[Any] = None,
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
            install_manager_flow(brain, bus, events, decide=decide,
                                 conv=brains.get("conv"))
        elif did in ("arm1", "arm2"):
            install_arm_flow(brain, bus, events, run_atomic=run_atomic)
            install_arm_gate(brain)  # DM-5 embodiment gate (real dont-know)

    mgr = brains["mgr"]

    def _resolve_brain(scope: Optional[str]) -> Optional[Any]:
        """Map an inbound export ``scope`` (a UI contract id like ``a1`` — or a
        device id) to the brain (PB-10)."""
        if not scope:
            return None
        device = scope if scope in brains else _CONTRACT_TO_DEVICE.get(scope)
        return brains.get(device) if device else None

    def _export_episode_audit(scope: Optional[str], respond) -> None:
        """Mode-A export: serialize the chosen brain's episode/reasoning audit
        OFF the WS loop (PB-8) and reply ``state_snapshot`` to the requester
        only (PB-16). A bad scope replies an honest, sanitized error snapshot
        rather than silence."""
        brain = _resolve_brain(scope)
        if respond is None:
            return
        if brain is None:
            respond(DemoEvents.snapshot_frame(
                {"snapshot_version": 1, "kind": KIND_EPISODE_AUDIT,
                 "error": "unknown brain", "brains": {}}))
            return

        def _work() -> None:
            try:
                snap = build_episode_audit_snapshot(brain)
                respond(DemoEvents.snapshot_frame(snap))
            except Exception as exc:  # never crash the server on an export
                respond(DemoEvents.snapshot_frame(
                    {"snapshot_version": 1, "kind": KIND_EPISODE_AUDIT,
                     "error": f"{type(exc).__name__}", "brains": {}}))

        threading.Thread(target=_work, name="export-mode-a", daemon=True).start()

    def on_command(name: str, args: dict, respond=None) -> None:
        if name == "place_order":
            # state-then-message (canonical — groups the order with this beat).
            events.state({"mgr": {"intent": "Interpret order",
                                  "decision": "understand the request",
                                  "chain": 1, "active": True}},
                         title="Order placed", narr="User submitted an order.")
            events.message("user", "mgr", "placed an order")
            run_task(mgr, {"order": args}, task_id="order")
        elif name == "export_state":
            mode = (args or {}).get("mode")
            if mode == KIND_EPISODE_AUDIT:
                _export_episode_audit((args or {}).get("scope"), respond)
            # mode "demo-state" (Mode B) is deferred post-DM-6 (nothing real to
            # warm-restore yet) — the UI mock covers it; live is not wired.
        elif name == "inject_fault":
            # DM-6: inject a recoverable perturbation (minor) or a persistent
            # freeze (major) on a target arm; "clear" removes the freeze. The
            # arm's verified-approach (run_atomic) catches the resulting
            # divergence and recalibrates or reports. No-op without a body.
            if sim_engine is not None:
                a = (args or {}).get("scope") or (args or {}).get("arm") or "a1"
                arm_n = 2 if str(a) in ("arm2", "a2") else 1
                kind = (args or {}).get("kind", "disturb")
                joint = int((args or {}).get("joint", 1))
                if kind == "freeze":
                    sim_engine.freeze_joint(arm_n, joint)
                elif kind == "clear":
                    sim_engine.clear_freezes(arm_n)
                else:
                    sim_engine.disturb_joint(
                        arm_n, joint, float((args or {}).get("delta", 0.03)))
        elif name == "reset":
            events.reset()
        # play/pause/step are mock-playback concepts; live runs on real orders.

    return on_command


# ── Server panel — server_status provider (DM-4) ──────────────────────
def make_status_provider(result: Any, *, endpoint: Optional[str] = None) -> Callable[[], dict]:
    """Build the ``() -> server_status frame`` provider from a BootstrapResult.

    Sessions are the real four ``login()`` Sessions (one per brain); ``since``
    is the boot timestamp (all four log in within the same bootstrap second —
    accurate to the second without depending on Session internals, PB-4/PB-19),
    ``uptime_s`` counts from process/server start, ``state_saved`` reflects the
    real Falkor Global persist. Sanitized (no version, "Storage: connected")."""
    start = time.time()
    since_iso = datetime.now(timezone.utc).isoformat()
    sessions: List[Dict[str, str]] = [
        {"device_id": did, "since": since_iso} for did in result.brains
    ]
    state_saved = bool(getattr(result, "persisted_global", False))

    def provider() -> dict:
        return server_status_frame(
            sessions,
            uptime_s=int(time.time() - start),
            storage_connected=True,
            state_saved=state_saved,
            endpoint=endpoint,
        )

    return provider


__all__ = [
    "wire_demo", "wire_brain_comms", "install_manager_flow", "install_arm_flow",
    "wire_pose_stream", "make_live_run_atomic", "make_status_provider", "RunAtomic",
]
