"""Collection-iteration — ``plan_construction.build`` wires a planner's ordered
``milestones`` shape into ``PlanResult`` (ADR-0199 / locked decision 3).

The map/fold executor (``execution.run``) shipped in Slices 1b/2/3b, but it was
reachable only by a test constructing a ``PlanResult`` by hand: ``build`` — the
sole producer on the real lifecycle path — never populated ``milestone_specs`` /
``leaf_targets``. These tests cover that wiring:

* a planner ``milestones`` list lands in ``PlanResult``, keyed to the refs core
  mints, in planner order (Option A);
* per-leaf ``leaf_target`` plumbing + plan-global ``solve_target`` coexist;
* no ``milestones`` (absent, empty, or malformed) is byte-identical to v0;
* end-to-end: a ``build``-produced plan drives the executor's real map/fold.

Unit tests drive ``build`` with a fake planner-dispatcher; the end-to-end test
runs the built plan over real capacities (mirrors ``test_slice1b_map_fold.py``).
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION,
    capacity_iri,
    datastate_iri,
)
from mindsos_capacity.builtins.planning_v0 import DS_IS_LEAF, DS_PLAN

from mindsos_intelligence import execution, plan_construction
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel

MAP_SPEC = {
    "kind": "map", "collection_ds": "ds.coll", "member_ds": "ds.mem",
    "sub_target": "ds.sub", "out_ds": "ds.out",
}
FOLD_SPEC = {"kind": "fold", "reducer_iri": "cap:reduce", "in_ds": "ds.out"}
GLOBAL_TARGET = {"start_datastate": "ds.a", "target_datastate": "ds.b"}


class _Out:
    def __init__(self, outputs):
        self.outputs = outputs


class FakePlanner:
    """Stands in for the L3 ``derive_initial_plan`` capacity: returns a fixed
    ``plan_out``; answers ``is_leaf`` True so the v0 fallback yields a lone leaf."""

    def __init__(self, plan_out, is_leaf=True):
        self.plan_out = plan_out
        self.is_leaf = is_leaf
        self.calls = []

    def dispatch(self, iri, inputs):
        self.calls.append(iri)
        if iri == plan_construction.DERIVE_PLAN_IRI:
            return _Out({DS_PLAN: self.plan_out})
        if iri == plan_construction.IS_LEAF_IRI:
            return _Out({DS_IS_LEAF: self.is_leaf})
        raise AssertionError(f"unexpected dispatch: {iri}")


def _writer():
    return ChainArtifactWriter(MentalModel(session_id="s", user_id="u"), "t")


def _build(plan_out, is_leaf=True):
    disp = FakePlanner(plan_out, is_leaf=is_leaf)
    res = plan_construction.build(
        disp, _writer(), "mr:1", "rp:1", resolved_reference="ref"
    )
    return res, disp


def test_milestones_populate_planresult_in_planner_order():
    plan_out = {
        "milestones": [{"spec": MAP_SPEC}, {"spec": FOLD_SPEC}],
        "solve_target": GLOBAL_TARGET,
    }
    res, disp = _build(plan_out)
    # Two leaves, in planner order; root is a distinct parent ref.
    assert len(res.leaf_milestone_refs) == 2
    assert res.root_milestone_ref not in res.leaf_milestone_refs
    # milestone_specs keyed to the emitted refs, in order.
    assert res.milestone_specs is not None
    specs_in_order = [res.milestone_specs[r] for r in res.leaf_milestone_refs]
    assert specs_in_order == [MAP_SPEC, FOLD_SPEC]
    # A pipeline per leaf; plan-global solve_target preserved; no leaf_targets.
    assert set(res.pipeline_refs) == set(res.leaf_milestone_refs)
    assert res.solve_target == GLOBAL_TARGET
    assert res.leaf_targets is None
    # The milestones path never touches the v0 decompose/is_leaf dispatch.
    assert plan_construction.IS_LEAF_IRI not in disp.calls


def test_leaf_target_plumbing_and_global_coexist():
    leaf_t = {"start_datastate": "ds.s", "target_datastate": "ds.t"}
    plan_out = {
        "milestones": [{"leaf_target": leaf_t}],  # a plain leaf, no spec
        "solve_target": GLOBAL_TARGET,
    }
    res, _ = _build(plan_out)
    assert res.milestone_specs is None
    assert res.leaf_targets == {res.leaf_milestone_refs[0]: leaf_t}
    assert res.solve_target == GLOBAL_TARGET  # AC#4: global still read


def test_no_milestones_is_byte_identical_to_empty_list():
    base = {"solve_target": GLOBAL_TARGET}                       # key absent
    empty = {"milestones": [], "solve_target": GLOBAL_TARGET}    # empty list
    r_base, _ = _build(base)
    r_empty, _ = _build(empty)
    # Fresh writers mint deterministic IRIs, so v0-equivalent plans are equal.
    assert r_base == r_empty
    # v0 shape: single leaf == root, no specs/targets.
    assert r_base.milestone_specs is None and r_base.leaf_targets is None
    assert len(r_base.leaf_milestone_refs) == 1
    assert r_base.root_milestone_ref == r_base.leaf_milestone_refs[0]


def test_malformed_milestones_falls_back_to_v0():
    plan_out = {"milestones": ["not-a-mapping"], "solve_target": GLOBAL_TARGET}
    res, disp = _build(plan_out)
    assert res.milestone_specs is None
    assert len(res.leaf_milestone_refs) == 1
    assert res.root_milestone_ref == res.leaf_milestone_refs[0]
    # Fell through to the v0 decompose path.
    assert plan_construction.IS_LEAF_IRI in disp.calls


# --- end-to-end: a build()-produced plan drives the real map/fold executor ---

E2E_COLL = datastate_iri("pw.coll")
E2E_MEMBER = datastate_iri("pw.mem")
E2E_SUB = datastate_iri("pw.sub")
E2E_OUT = datastate_iri("pw.out")
E2E_AGG = datastate_iri("pw.agg")
E2E_REDUCE = capacity_iri(CATEGORY_DERIVATION, "pw_reduce")

_MEMBER_SEEN: list = []
_REDUCER_SEEN: list = []


class _FakeSession:
    def __init__(self):
        self.session_id = "s"
        self.user_id = "u"
        self.actor_role = "user"
        self.capabilities = set()

    def has(self, capability):
        return False


def _member_body(**kw):
    v = kw.get(E2E_MEMBER)
    _MEMBER_SEEN.append(v)
    return {E2E_SUB: {"solved": v}}


def _reduce_body(**kw):
    ordered = kw.get(E2E_OUT)
    _REDUCER_SEEN.append(ordered)
    return {E2E_AGG: {"conclusion": ordered}}


def _register(layer, session):
    specs = {
        "pw.coll": dict(collection=True, member_ds=E2E_MEMBER),
        "pw.out": dict(collection=True, member_ds=E2E_SUB),
    }
    for name in ("pw.coll", "pw.mem", "pw.sub", "pw.out", "pw.agg"):
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
            name="pw_member", category=CATEGORY_DERIVATION,
            inputs=(E2E_MEMBER,), outputs=(E2E_SUB,), implementation=_member_body,
            description="member: mem -> sub",
        ),
        session=session,
    )
    layer.register_capacity(
        Capacity(
            name="pw_reduce", category=CATEGORY_DERIVATION,
            inputs=(E2E_OUT,), outputs=(E2E_AGG,), implementation=_reduce_body,
            description="reducer: out -> agg",
        ),
        session=session,
    )


def test_built_plan_reaches_executor_map_fold():
    _MEMBER_SEEN.clear()
    _REDUCER_SEEN.clear()
    map_spec = {
        "kind": "map", "collection_ds": E2E_COLL, "member_ds": E2E_MEMBER,
        "sub_target": E2E_SUB, "out_ds": E2E_OUT,
    }
    fold_spec = {"kind": "fold", "reducer_iri": E2E_REDUCE, "in_ds": E2E_OUT}
    plan_out = {"milestones": [{"spec": map_spec}, {"spec": fold_spec}]}

    mm = MentalModel(session_id="s", user_id="u")
    writer = ChainArtifactWriter(mm, "t")
    # Produce the plan through the real builder (fake planner-dispatch only).
    plan_result = plan_construction.build(
        FakePlanner(plan_out), writer, "mr:1", "rp:1", resolved_reference="ref"
    )
    assert plan_result.milestone_specs is not None  # build populated the shape

    # Run it for real over registered capacities.
    sess = _FakeSession()
    layer = CapacityLayer()
    _register(layer, sess)
    disp = L4Dispatcher(layer, session=sess)
    request_run = writer.emit_request_run()
    graphs: list = []
    execution.run(
        disp, writer, plan_result, request_run,
        mm=mm, run_scope="t",
        solve_seed={E2E_COLL: [{"m": 0}, {"m": 1}, {"m": 2}]},
        capacity_graphs=graphs,
    )
    # Fan-out in collection order; fold got the ordered member outputs.
    assert _MEMBER_SEEN == [{"m": 0}, {"m": 1}, {"m": 2}]
    assert _REDUCER_SEEN == [[
        {"solved": {"m": 0}}, {"solved": {"m": 1}}, {"solved": {"m": 2}},
    ]]
    assert len(request_run.pipeline_runs) == 2  # map + fold
