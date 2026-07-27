"""Collection-iteration Slice 3b — targeted (per-member) RE-EXECUTION.

Slice 3 made replan/diagnosis *address* a suspect map member (advisory only);
replan execution stayed whole-pipeline. Slice 3b lets the orchestrator ACT on
that address: when the verdict names a re-runnable **top-level flat map** member
(reserved ``"map"``/``"plan_subtree"`` level + a resolvable ref-path), it
invalidates only that map + fold + downstream and re-runs just that one member,
reusing the completed siblings' values off a **retained** blackboard.

Option A (owner-approved): the member is addressed by its existing Slice-2
grounding ref-path — no promotion of members to first-class chain PipelineRuns
(that, plus cross-stage continuity, is the deferred B/continuity slice). The path
is **additive-inert**: a v0 verdict, a full ``pipelinerun:`` advisory ref, or a
nested target all resolve to ``None`` → whole-pipeline replan, byte-identical to
Slice 3 (its two tests pass unchanged).

Coverage: (1) ``resolve_member_target`` accepts only the bare top-level form;
(2) ``invalidate_at_and_below(at_index=…)`` keeps the prefix; (3) execution-level
end-to-end — a targeted re-run touches only the named member, keeps the siblings,
and re-fires the fold; (4) orchestrator wiring — a targeted verdict retains the
blackboard across the loop and passes ``targeted`` into ``execution.run``.
No Falkor.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION,
    capacity_iri,
    datastate_iri,
)

from mindsos_intelligence import execution, plan_construction, replan_check
from mindsos_intelligence.chain_artifacts import (
    ChainArtifactWriter,
    ReplanVerdict,
    RequestRun,
    TYPE_REPLAN_RECORD,
    iter_chain_artifacts,
)
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

DS_COLL = datastate_iri("s3b.grids")
DS_MEMBER = datastate_iri("s3b.grid")
DS_SUB = datastate_iri("s3b.grid_fact")
DS_OUT = datastate_iri("s3b.grid_facts")
DS_AGG = datastate_iri("s3b.conclusion")

CAP_REDUCE = capacity_iri(CATEGORY_DERIVATION, "s3b_reduce")

MEMBER_SEEN: list = []
REDUCER_SEEN: list = []
GEN: dict = {"n": 0}


class FakeSession:
    def __init__(self, user_id="u"):
        self.session_id = "s"
        self.user_id = user_id
        self.actor_role = "user"
        self.capabilities = set()

    def has(self, capability: str) -> bool:
        return False


def _member_body(**kwargs):
    v = kwargs.get(DS_MEMBER)
    MEMBER_SEEN.append(v)
    GEN["n"] += 1
    # ``gen`` makes a re-run's output distinguishable from the first run's, so a
    # spliced member and a re-fired fold are observable.
    return {DS_SUB: {"solved": v, "gen": GEN["n"]}}


def _reduce_body(**kwargs):
    ordered = kwargs.get(DS_OUT)
    REDUCER_SEEN.append(ordered)
    return {DS_AGG: {"conclusion": ordered}}


def _register(layer, *, session=None):
    specs = {
        "s3b.grids": dict(collection=True, member_ds=DS_MEMBER),
        "s3b.grid_facts": dict(collection=True, member_ds=DS_SUB),
    }
    for name in ("s3b.grids", "s3b.grid", "s3b.grid_fact", "s3b.grid_facts", "s3b.conclusion"):
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=name,
                provenance_category=CATEGORY_DERIVATION,
                **specs.get(name, {}),
            ),
            session=session,
            allow_new_realm=True,
        )
    layer.register_capacity(
        Capacity(
            name="s3b_member_solve", category=CATEGORY_DERIVATION,
            inputs=(DS_MEMBER,), outputs=(DS_SUB,), implementation=_member_body,
            description="member: grid -> grid_fact",
        ),
        session=session,
    )
    layer.register_capacity(
        Capacity(
            name="s3b_reduce", category=CATEGORY_DERIVATION,
            inputs=(DS_OUT,), outputs=(DS_AGG,), implementation=_reduce_body,
            description="reducer: grid_facts -> conclusion",
        ),
        session=session,
    )


def _map_fold_plan():
    return PlanResult(
        plan_ref="plan:3b",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mMap", "mFold"],
        pipeline_refs={"mMap": "pMap", "mFold": "pFold"},
        milestone_specs={
            "mMap": {
                "kind": "map", "collection_ds": DS_COLL, "member_ds": DS_MEMBER,
                "sub_target": DS_SUB, "out_ds": DS_OUT,
            },
            "mFold": {"kind": "fold", "reducer_iri": CAP_REDUCE, "in_ds": DS_OUT},
        },
    )


def _harness():
    sess = FakeSession()
    layer = CapacityLayer()
    _register(layer, session=sess)
    mm = MentalModel(session_id="s", user_id="u")
    disp = L4Dispatcher(layer, session=sess)
    writer = ChainArtifactWriter(mm, "t")
    request_run = writer.emit_request_run()
    return mm, disp, writer, request_run


# ── unit: resolve_member_target ─────────────────────────────────────────────


def test_resolve_member_target_accepts_bare_top_level_form():
    plan = _map_fold_plan()
    assert execution.resolve_member_target(plan, "0:m1") == (0, 1)


def test_resolve_member_target_rejects_full_ref_and_nested_and_non_map():
    plan = _map_fold_plan()
    # Full Slice-3 advisory ref (scope may hold ':') → advisory-only fallback.
    assert execution.resolve_member_target(plan, "pipelinerun:t:0:m1:0:r0") is None
    # Nested path (interleaved PipelineRuns) → deferred → None.
    assert execution.resolve_member_target(plan, "0:m1:0:m2") is None
    # Fold milestone is not a map.
    assert execution.resolve_member_target(plan, "1:m0") is None
    # Out-of-range leaf, and a malformed member segment.
    assert execution.resolve_member_target(plan, "9:m0") is None
    assert execution.resolve_member_target(plan, "0:x1") is None


def test_resolve_member_target_rejects_map_with_sub_plan():
    plan = _map_fold_plan()
    plan.milestone_specs["mMap"]["sub_plan"] = {"leaf_milestone_refs": []}
    assert execution.resolve_member_target(plan, "0:m0") is None


# ── unit: invalidate_at_and_below(at_index=…) ───────────────────────────────


def test_invalidate_at_index_keeps_prefix():
    rr = RequestRun(iri="rr", pipeline_runs=["a", "b", "c", "d"])
    invalidated = replan_check.invalidate_at_and_below(rr, "map", at_index=1)
    assert invalidated == ["b", "c", "d"]
    assert rr.pipeline_runs == ["a"]


def test_invalidate_none_clears_all_byte_identical():
    rr = RequestRun(iri="rr", pipeline_runs=["a", "b", "c"])
    invalidated = replan_check.invalidate_at_and_below(rr, "pipeline")
    assert invalidated == ["a", "b", "c"]
    assert rr.pipeline_runs == []


# ── execution-level: targeted re-run touches only the named member ──────────


def test_targeted_reexec_reruns_only_named_member_keeps_siblings_refires_fold():
    MEMBER_SEEN.clear()
    REDUCER_SEEN.clear()
    GEN["n"] = 0
    mm, disp, writer, request_run = _harness()
    graphs: list = []
    bb = {DS_COLL: [{"m": 0}, {"m": 1}, {"m": 2}]}

    # First full run: three members (gens 1,2,3), fold once.
    execution.run(
        disp, writer, _map_fold_plan(), request_run,
        mm=mm, run_scope="t", solve_seed=bb, blackboard=bb, capacity_graphs=graphs,
    )
    assert MEMBER_SEEN == [{"m": 0}, {"m": 1}, {"m": 2}]
    assert [o["gen"] for o in bb[DS_OUT]] == [1, 2, 3]
    assert len(request_run.pipeline_runs) == 2

    # Targeted replan of member 1: invalidate at the map position, then re-run
    # ONLY member 1 against the retained blackboard at a fresh run_attempt.
    replan_check.invalidate_at_and_below(request_run, "map", at_index=0)
    MEMBER_SEEN.clear()
    execution.run(
        disp, writer, _map_fold_plan(), request_run,
        mm=mm, run_scope="t", solve_seed=bb, blackboard=bb,
        targeted=(0, 1), run_attempt=1, capacity_graphs=graphs,
    )
    # Only member 1 re-ran; siblings 0 and 2 kept their original outputs.
    assert MEMBER_SEEN == [{"m": 1}]
    assert [o["gen"] for o in bb[DS_OUT]] == [1, 4, 3]
    # The fold re-fired over the spliced list (member 1 now gen 4).
    assert REDUCER_SEEN[-1] == [
        {"solved": {"m": 0}, "gen": 1},
        {"solved": {"m": 1}, "gen": 4},
        {"solved": {"m": 2}, "gen": 3},
    ]
    # Prefix kept none (map at index 0); map + fold re-emitted → 2 again.
    assert len(request_run.pipeline_runs) == 2


def test_full_run_unchanged_when_not_targeted():
    """No ``targeted``/``blackboard`` → fresh seed, full fan-out — the Slice-1b
    contract, unchanged (byte-identical additive-inertness guard)."""
    MEMBER_SEEN.clear()
    REDUCER_SEEN.clear()
    GEN["n"] = 0
    mm, disp, writer, request_run = _harness()
    execution.run(
        disp, writer, _map_fold_plan(), request_run,
        mm=mm, run_scope="t",
        solve_seed={DS_COLL: [{"m": 0}, {"m": 1}]}, capacity_graphs=[],
    )
    assert MEMBER_SEEN == [{"m": 0}, {"m": 1}]
    assert len(REDUCER_SEEN[-1]) == 2
    assert len(request_run.pipeline_runs) == 2


# ── orchestrator wiring: retain blackboard + pass targeted into execution ───


def test_orchestrator_targeted_replan_retains_blackboard_and_wires_execution(monkeypatch):
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_capacity.builtins import install_phase1_v0
    from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
    from mindsos_capacity.builtins.orchestration_v0 import (
        DS_REPLAN_STATE,
        DS_REPLAN_VERDICT,
        build_attention_score,
        build_signal_to_tier,
        build_sufficient,
        reset_v0_verdicts,
        set_sufficient_result,
        _orchestration_datastates,
    )
    from mindsos_capacity.identifiers import CATEGORY_DECISION
    from mindsos_intelligence.orchestrator import Orchestrator

    calls: list = []
    state = {"replan_calls": 0}

    def _fake_run(dispatcher, writer, plan_result, request_run, *, mm=None,
                  run_scope=None, solve_seed=None, capacity_graphs=None,
                  run_attempt=0, blackboard=None, targeted=None):
        calls.append({"targeted": targeted, "bb_id": id(blackboard), "attempt": run_attempt})
        request_run.pipeline_runs.append(f"pr{run_attempt}a")
        request_run.pipeline_runs.append(f"pr{run_attempt}b")
        return []

    map_plan = _map_fold_plan()
    map_plan.solve_target = {"start_datastate": DS_MEMBER, "target_datastate": DS_SUB}

    def _fake_build(*a, **k):
        return map_plan

    def _replan_once_naming_member(**kwargs):
        state["replan_calls"] += 1
        decision = "replan" if state["replan_calls"] == 1 else "continue"
        return {DS_REPLAN_VERDICT: {
            "decision": decision, "verified": True, "divergence": 0.0,
            "replan_level": "map", "target_ref": "0:m1",
        }}

    monkeypatch.setattr(execution, "run", _fake_run)
    monkeypatch.setattr(plan_construction, "build", _fake_build)

    reset_v0_verdicts()
    set_sufficient_result(True)
    try:
        kl = KnowledgeLayer.bootstrap()
        layer = CapacityLayer(kl=kl)
        install_phase1_v0(layer)
        for ds in _orchestration_datastates():
            layer.register_datastate(ds, allow_new_realm=True)
        layer.register_capacity(build_signal_to_tier())
        layer.register_capacity(build_attention_score())
        layer.register_capacity(build_sufficient())
        layer.register_capacity(
            Capacity(
                name="should_replan", category=CATEGORY_DECISION,
                inputs=(DS_REPLAN_STATE,), outputs=(DS_REPLAN_VERDICT,),
                implementation=_replan_once_naming_member,
                description="test: replan once naming member 0:m1",
                placeholder=True,
            )
        )
        install_consolidate_capacities(layer)
        mm = MentalModel(session_id="s", user_id="u")
        disp = L4Dispatcher(layer, session=FakeSession(), kl=kl)
        orch = Orchestrator(disp, mm, request_scope="task-1")
        outcome = orch.run_lifecycle("hello", request_id="T")
    finally:
        reset_v0_verdicts()

    assert outcome.status == "succeeded"
    # execution.run ran twice: a full first pass, then a TARGETED re-run.
    assert len(calls) == 2
    assert calls[0]["targeted"] is None
    assert calls[1]["targeted"] == (0, 1)
    # The blackboard object was RETAINED across the targeted replan (not reset).
    assert calls[0]["bb_id"] == calls[1]["bb_id"]
    # The recorded replan is the ACTUAL targeted level (not "pipeline").
    records = [v for _, v in iter_chain_artifacts(mm, TYPE_REPLAN_RECORD)]
    assert len(records) == 1
    assert records[0].replan_level == "map"
    assert records[0].replan_milestone_ref == "0:m1"
