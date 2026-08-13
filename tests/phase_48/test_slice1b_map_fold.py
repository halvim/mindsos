"""Collection-iteration Slice 1b — map fan-out + fold + ∀-abort barrier + retry.

Slice 1a threaded values across milestones; 1b adds the map/fold plan primitive
on top of that bus. A ``map`` milestone fans a uniform sub-pipeline out over the
ordered members of a collection DataState (ADR-0199) — sequentially (v1), each
member in an isolated sub-blackboard seeded with just the member value, with
bounded retry (``MEMBER_RETRY_CAP``) and an all-or-nothing barrier — and writes
the ordered member outputs to the blackboard. A ``fold`` milestone dispatches an
L3 reducer over that ordered list. These tests exercise the primitive over real
capacities (no Falkor), mirroring ``test_slice1a_value_bus.py``.
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

from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

DS_COLL = datastate_iri("s1b.grids")       # collection of members
DS_MEMBER = datastate_iri("s1b.grid")      # one member
DS_SUB = datastate_iri("s1b.grid_fact")    # per-member sub-target output
DS_OUT = datastate_iri("s1b.grid_facts")   # ordered member outputs (map out / fold in)
DS_AGG = datastate_iri("s1b.conclusion")   # fold aggregate

CAP_SOLVE = capacity_iri(CATEGORY_DERIVATION, "s1b_member_solve")  # member -> sub
CAP_REDUCE = capacity_iri(CATEGORY_DERIVATION, "s1b_reduce")       # out -> agg

#: What each member sub-run received (proves fan-out + order), and what the
#: reducer received (proves the fold got the ordered member outputs).
MEMBER_SEEN: list = []
REDUCER_SEEN: list = []
ATTEMPTS: dict = {}


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
    return {DS_SUB: {"solved": v}}


def _reduce_body(**kwargs):
    ordered = kwargs.get(DS_OUT)
    REDUCER_SEEN.append(ordered)
    return {DS_AGG: {"conclusion": ordered}}


def _register(layer, member_impl, *, session=None):
    specs = {
        "s1b.grids": dict(collection=True, member_ds=DS_MEMBER),
        "s1b.grid_facts": dict(collection=True, member_ds=DS_SUB),
    }
    for name in ("s1b.grids", "s1b.grid", "s1b.grid_fact", "s1b.grid_facts", "s1b.conclusion"):
        extra = specs.get(name, {})
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=name,
                provenance_category=CATEGORY_DERIVATION,
                **extra,
            ),
            session=session,
            allow_new_realm=True,
        )
    layer.register_capacity(
        Capacity(
            name="s1b_member_solve", category=CATEGORY_DERIVATION,
            inputs=(DS_MEMBER,), outputs=(DS_SUB,), implementation=member_impl,
            description="member: grid -> grid_fact",
        ),
        session=session,
    )
    layer.register_capacity(
        Capacity(
            name="s1b_reduce", category=CATEGORY_DERIVATION,
            inputs=(DS_OUT,), outputs=(DS_AGG,), implementation=_reduce_body,
            description="reducer: grid_facts -> conclusion",
        ),
        session=session,
    )


def _map_fold_plan():
    return PlanResult(
        plan_ref="plan:1b",
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


def _harness(member_impl):
    sess = FakeSession()
    layer = CapacityLayer()
    _register(layer, member_impl, session=sess)
    mm = MentalModel(session_id="s", user_id="u")
    disp = L4Dispatcher(layer, session=sess)
    writer = ChainArtifactWriter(mm, "t")
    request_run = writer.emit_request_run()
    return mm, disp, writer, request_run


def test_map_fans_out_and_fold_reduces_in_order():
    MEMBER_SEEN.clear()
    REDUCER_SEEN.clear()
    mm, disp, writer, request_run = _harness(_member_body)
    graphs: list = []
    execution.run(
        disp, writer, _map_fold_plan(), request_run,
        mm=mm, run_scope="t",
        solve_seed={DS_COLL: [{"m": 0}, {"m": 1}, {"m": 2}]},
        capacity_graphs=graphs,
    )
    # Fan-out: every member ran, in collection order.
    assert MEMBER_SEEN == [{"m": 0}, {"m": 1}, {"m": 2}]
    # Fold: the reducer received the members' outputs as one ordered list.
    assert REDUCER_SEEN == [[
        {"solved": {"m": 0}}, {"solved": {"m": 1}}, {"solved": {"m": 2}},
    ]]
    # Two milestone PipelineRuns (map + fold); one grounding graph per member
    # PLUS the fold's own (fold-grounding CR — the fold used to leave nothing).
    assert len(request_run.pipeline_runs) == 2
    assert len(graphs) == 4


def test_all_abort_on_member_failure_skips_rest_and_fold():
    MEMBER_SEEN.clear()
    REDUCER_SEEN.clear()

    def _fail_member_1(**kwargs):
        v = kwargs.get(DS_MEMBER)
        MEMBER_SEEN.append(v)
        if v == {"m": 1}:
            raise RuntimeError("member 1 load failure")
        return {DS_SUB: {"solved": v}}

    mm, disp, writer, request_run = _harness(_fail_member_1)
    with pytest.raises(execution.MemberAbortError) as ei:
        execution.run(
            disp, writer, _map_fold_plan(), request_run,
            mm=mm, run_scope="t",
            solve_seed={DS_COLL: [{"m": 0}, {"m": 1}, {"m": 2}]},
            capacity_graphs=[],
        )
    assert ei.value.member_index == 1
    # Member 1 retried up to the cap; member 2 never ran; the fold never ran.
    assert MEMBER_SEEN.count({"m": 1}) == execution.MEMBER_RETRY_CAP
    assert {"m": 2} not in MEMBER_SEEN
    assert REDUCER_SEEN == []


def test_bounded_retry_accepts_first_clean_attempt():
    MEMBER_SEEN.clear()
    REDUCER_SEEN.clear()
    ATTEMPTS.clear()

    def _fail_once(**kwargs):
        v = kwargs.get(DS_MEMBER)
        key = tuple(sorted(v.items()))
        ATTEMPTS[key] = ATTEMPTS.get(key, 0) + 1
        MEMBER_SEEN.append(v)
        if v == {"m": 1} and ATTEMPTS[key] == 1:
            raise RuntimeError("transient load failure")
        return {DS_SUB: {"solved": v}}

    mm, disp, writer, request_run = _harness(_fail_once)
    execution.run(
        disp, writer, _map_fold_plan(), request_run,
        mm=mm, run_scope="t",
        solve_seed={DS_COLL: [{"m": 0}, {"m": 1}, {"m": 2}]},
        capacity_graphs=[],
    )
    # Member 1 failed once then succeeded within the cap; all three fold in order.
    assert ATTEMPTS[(("m", 1),)] == 2
    assert REDUCER_SEEN == [[
        {"solved": {"m": 0}}, {"solved": {"m": 1}}, {"solved": {"m": 2}},
    ]]


def test_no_specs_plan_is_plain_leaf_unchanged():
    """A plan without ``milestone_specs`` runs the plain-leaf path (Slice 1a),
    proving 1b is inert unless a map/fold spec is present."""
    MEMBER_SEEN.clear()
    REDUCER_SEEN.clear()
    mm, disp, writer, request_run = _harness(_member_body)
    plan = PlanResult(
        plan_ref="plan:leaf",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mA"],
        pipeline_refs={"mA": "pA"},
        leaf_targets={"mA": {"start_datastate": DS_MEMBER, "target_datastate": DS_SUB}},
    )
    execution.run(
        disp, writer, plan, request_run,
        mm=mm, run_scope="t",
        solve_seed={DS_MEMBER: {"m": 9}}, capacity_graphs=[],
    )
    # Ran the single leaf as a normal pipeline; no map fan-out, no fold.
    assert MEMBER_SEEN == [{"m": 9}]
    assert REDUCER_SEEN == []
    assert len(request_run.pipeline_runs) == 1
