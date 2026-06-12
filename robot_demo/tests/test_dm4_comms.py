"""DM-4 — end-to-end gate flow in the 3.10 sandbox (no MuJoCo).

Proves the DM-4 gate with real mindsos stacks, minus the body (the arm's
atomic is an injected stub here; the Linux gate swaps in the real move_to):

    mgr run_lifecycle
      -> (phase-2 override) comms.dispatch  --bus-->  arm
                                                       arm run_lifecycle
                                                         -> (phase-2 override) run_atomic(target)
                                                       <-- comms.report --
      <-- ack
    both Episodes consolidate.

Also confirms PB-BBB (the ``interaction`` category registers) and PB-EEE
(the target round-trips through task_pattern_iri) against real code.
"""

from __future__ import annotations

import pytest

from robot_demo.backend.brain import build_brain_stack
from robot_demo.backend.profiles import DEVICE_PROFILES
from robot_demo.backend.installers import install_core_datastates
from robot_demo.backend.bus import BrainBus
from robot_demo.backend.comms import (
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

from mindsos_capacity.builtins.phase1_v0 import DS_STRUCTURED_INPUT, DS_MAPPING
from mindsos_capacity.builtins.planning_v0 import DS_PLAN, DS_MAPPING_RESULT
from mindsos_intelligence.phase_1 import PROCESS_IRI, MAP_IRI
from mindsos_intelligence.plan_construction import DERIVE_PLAN_IRI


class _DuckSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.session_id = f"sess-{user_id}"
        self.actor_role = "user"
        self.capabilities = frozenset()

    def has(self, capability):
        return True


def _episode_count(brain):
    from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
    from mindsos_knowledge.metagraph_view import MetagraphView
    g = MetagraphView(brain.kl.local_metagraph(brain.device_id)).graphs_by_role(
        ROLE_EPISODIC_MEMORIES
    )[0]
    return sum(1 for n in g.nodes.values()
               if getattr(n, "type_name", None) == "Episode")


def test_dm4_gate_end_to_end():
    mgr = build_brain_stack(DEVICE_PROFILES["mgr"], _DuckSession("mgr"))
    arm = build_brain_stack(DEVICE_PROFILES["arm1"], _DuckSession("arm1"))
    bus = BrainBus()
    bus.register_endpoint("mgr")
    bus.register_endpoint("a1")

    # robot.* DataStates into each brain's Global (DM-2 path, called directly)
    for b in (mgr, arm):
        install_core_datastates(b.cl)

    register_comms_capacities(mgr.cl, bus, "mgr")
    register_comms_capacities(arm.cl, bus, "a1")

    trace = {}

    # ── arm-side overrides: process identity → map encodes target → derive
    #    decodes + runs the (stub) atomic inside the arm's own lifecycle ──
    def arm_process(context=None, **inputs):
        raw = next(iter(inputs.values()), None)
        return {DS_STRUCTURED_INPUT: raw}

    def arm_map(context=None, **inputs):
        structured = inputs.get(DS_STRUCTURED_INPUT) or {}
        cmd = structured.get("order") if isinstance(structured, dict) else {}
        target = (cmd or {}).get("target", "home")
        return {DS_MAPPING: {"task_pattern_iri": encode_target("a1", target),
                             "mapping_confidence": 1.0}}

    def run_atomic(target):
        # the Linux gate swaps in arm.cl.invoke(a1.move_to, {DS_POSE_TARGET: target})
        trace["arm_ran_target"] = target
        return {"ok": True}

    def arm_derive(context=None, **inputs):
        mr = inputs.get(DS_MAPPING_RESULT) or {}
        _dst, target = decode_target(mr.get("task_pattern_iri", ""))
        run_atomic(target)
        return {DS_PLAN: {"executed": target}}

    install_override(arm.cl, PROCESS_IRI, arm_process)
    install_override(arm.cl, MAP_IRI, arm_map)
    install_override(arm.cl, DERIVE_PLAN_IRI, arm_derive)

    bus.set_handler(
        "a1", KIND_DISPATCH,
        make_dispatch_handler(bus, arm, build_task_input=lambda cmd: {"order": cmd}),
    )

    # ── mgr-side overrides: map decides (arm, target) → derive dispatches ──
    def mgr_map(context=None, **inputs):
        # thin slice: fixed allocation a1/home (DM-5 does real matching)
        return {DS_MAPPING: {"task_pattern_iri": encode_target("a1", "home"),
                             "mapping_confidence": 1.0}}

    def mgr_derive(context=None, **inputs):
        try:
            mr = inputs.get(DS_MAPPING_RESULT) or {}
            dst, target = decode_target(mr.get("task_pattern_iri", ""))
            cmd = {"dst": dst, "capacity": "move_to", "target": target,
                   "task_id": "order-1-sub"}
            res = mgr.cl.invoke(DISPATCH_IRI, {DS_DISPATCH_CMD: cmd}, session=None)
            trace["mgr_invoke_success"] = res.success
            trace["mgr_invoke_error"] = repr(getattr(res, "error", None))
            trace["mgr_ack"] = res.outputs.get(DS_DISPATCH_ACK)
        except Exception as exc:  # noqa
            trace["mgr_derive_err"] = f"{type(exc).__name__}: {exc}"
        return {DS_PLAN: {"dispatched": True}}

    install_override(mgr.cl, MAP_IRI, mgr_map)
    install_override(mgr.cl, DERIVE_PLAN_IRI, mgr_derive)

    # ── run the Manager lifecycle (the WS place_order entry point) ──
    fut = mgr.il.enqueue(
        lambda: mgr.orch.run_lifecycle({"order": "R0c0<-sheet"}, task_id="order-1")
    )
    outcome = fut.result(timeout=30)

    try:
        # gate assertions
        assert outcome.status == "succeeded", outcome.status
        assert trace.get("arm_ran_target") == "home"            # PB-EEE round-trip
        ack = trace.get("mgr_ack")
        assert ack is not None and ack.get("status") == "succeeded", ack
        assert ack.get("from") == "a1"                          # report came from the arm
        assert _episode_count(mgr) >= 1                          # mgr consolidated
        assert _episode_count(arm) >= 1                          # arm consolidated
    finally:
        bus.stop()
        mgr.il.stop()
        arm.il.stop()


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
