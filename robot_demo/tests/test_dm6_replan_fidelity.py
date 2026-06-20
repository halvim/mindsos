"""DM-6 — Fork-1 fidelity: the real lifecycle mints a real ReplanRecord /
BlameVerdict that the serializer renders, sanitized, on the MANAGER chain.

Sandbox-runnable (build_brain_stack needs no MuJoCo). Unlike the throwaway probe
(which used the global `set_should_replan_decision` test helper), this exercises
the **actual `install_override` seam** the DM-6 build relies on — de-risking the
manager should_replan slice (task 6) and locking Fork-1 = "honest thin marker"
(design-log §25 Fork 1): the orchestrator-minted record is real + clean, and the
real `divergence` magnitude flows through (no longer the 0.0 v0 stub).
"""

from __future__ import annotations

from mindsos_capacity.builtins.orchestration_v0 import DS_REPLAN_VERDICT, DS_SUFFICIENT
from mindsos_intelligence.replan_check import SHOULD_REPLAN_IRI
from mindsos_intelligence.sufficient_predicate import SUFFICIENT_IRI

from robot_demo.backend.brain import build_brain_stack, run_task
from robot_demo.backend.comms import install_override
from robot_demo.backend.profiles import DEVICE_PROFILES
from robot_demo.backend.sanitize import find_leaks
from robot_demo.backend.serializer import build_episode_audit_snapshot


class _Duck:
    def __init__(self, u):
        self.user_id = u
        self.session_id = f"s-{u}"
        self.actor_role = "user"
        self.capabilities = frozenset()

    def has(self, c):
        return False


def _make_one_shot_replan(divergence):
    """should_replan override: 'replan' once (carrying a REAL divergence), then
    'continue' — the one-shot stash pattern the manager reroute will use."""
    state = {"fired": False}

    def impl(context=None, **inputs):
        if not state["fired"]:
            state["fired"] = True
            return {DS_REPLAN_VERDICT: {"decision": "replan", "verified": True,
                                        "divergence": divergence}}
        return {DS_REPLAN_VERDICT: {"decision": "continue", "verified": True,
                                    "divergence": 0.0}}

    return impl


def test_replan_record_is_real_renders_and_clean():
    b = build_brain_stack(DEVICE_PROFILES["mgr"], _Duck("mgr"))
    try:
        install_override(b.cl, SHOULD_REPLAN_IRI, _make_one_shot_replan(0.42))
        out = run_task(b, {"text": "replan-fidelity"}, task_id="t").result(timeout=30)

        # Recovery shape: replanned, then completed -> "succeeded" + replans>0
        assert out.status == "succeeded"
        assert out.replans_used >= 1

        snap = build_episode_audit_snapshot(b)
        r = snap["brains"]["mgr"]["episodes"][0]["reasoning"]
        assert r["replans"], "expected a real ReplanRecord on the manager chain"
        e = r["replans"][0]
        assert e["replan_level"] == "pipeline"
        assert e["verdict"]["decision"] == "replan"
        # the REAL divergence flows through (no longer the 0.0 v0 stub)
        assert e["verdict"]["divergence"] == 0.42
        assert e["iri"].startswith("n")          # opaque token (PB-13)
        # honest thin marker: no fabricated rationale field on the record
        assert "rationale" not in e
        assert find_leaks(snap) == []            # clean wire (policy B)
    finally:
        b.il.stop()


def test_blame_and_dont_know_are_real_and_clean():
    b = build_brain_stack(DEVICE_PROFILES["mgr"], _Duck("mgr"))
    try:
        install_override(b.cl, SUFFICIENT_IRI, lambda context=None, **i: {DS_SUFFICIENT: False})
        out = run_task(b, {"text": "deadend"}, task_id="t").result(timeout=30)

        assert out.status == "dont_know"
        snap = build_episode_audit_snapshot(b)
        r = snap["brains"]["mgr"]["episodes"][0]["reasoning"]
        assert r["blame"] is not None and r["blame"]["chain_level"] == "pipeline"
        assert r["dont_know"] is not None
        assert find_leaks(snap) == []
    finally:
        b.il.stop()
