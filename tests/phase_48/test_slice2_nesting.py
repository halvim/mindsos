"""Collection-iteration Slice 2 — nesting (a map's sub-plan itself maps/folds).

Slice 1b gave one level of map/fold; Slice 2 lets a map member run a whole
sub-plan that may itself contain a map/fold (objects within grids within a
task). The core change is the per-member run-ref becoming a **path** so a nested
run's grounding graph stays isolated from its siblings and the provenance tree
(the set of per-run graphs, keyed by role) is walkable by path.

These tests exercise a two-level nest over real capacities (no Falkor), mirroring
``test_slice1b_map_fold.py``:

* an outer map over ``grids`` whose per-grid sub-plan is an inner map over that
  grid's ``objects`` + an inner fold — the whole thing folded once more at the
  top. Asserts every object ran in order, both fold levels reduced in order, and
  the four nested per-object grounding graphs carry **distinct role tokens that
  encode the nesting path** (isolation — the Slice-2 core change).
* an inner-member load failure raises ``MemberAbortError`` that propagates
  unretried through the outer member, skips the rest, and runs neither fold.
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
from mindsos_intelligence.capacity_mm_writer import run_graph_role
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

DS_GRIDS = datastate_iri("s2.grids")          # outer collection (of grids)
DS_GRID = datastate_iri("s2.grid")            # one grid == inner collection (of objects)
DS_OBJECT = datastate_iri("s2.object")        # one object (innermost member)
DS_OBJFACT = datastate_iri("s2.object_fact")  # per-object sub-target
DS_OBJFACTS = datastate_iri("s2.object_facts")  # ordered object outputs (inner map out / inner fold in)
DS_GRIDFACT = datastate_iri("s2.grid_fact")   # per-grid sub-target (inner fold out; outer map collects this)
DS_GRIDFACTS = datastate_iri("s2.grid_facts")  # ordered grid outputs (outer map out / outer fold in)
DS_CONCLUSION = datastate_iri("s2.conclusion")  # top fold aggregate

CAP_OBJ_SOLVE = capacity_iri(CATEGORY_DERIVATION, "s2_object_solve")   # object -> object_fact
CAP_OBJ_REDUCE = capacity_iri(CATEGORY_DERIVATION, "s2_object_reduce")  # object_facts -> grid_fact
CAP_GRID_REDUCE = capacity_iri(CATEGORY_DERIVATION, "s2_grid_reduce")   # grid_facts -> conclusion

#: What each innermost object sub-run received (proves the double fan-out + order),
#: and what each fold level received (proves the ordered hand-off at both levels).
OBJ_SEEN: list = []
OBJ_REDUCER_SEEN: list = []
GRID_REDUCER_SEEN: list = []
ATTEMPTS: dict = {}


class FakeSession:
    def __init__(self, user_id="u"):
        self.session_id = "s"
        self.user_id = user_id
        self.actor_role = "user"
        self.capabilities = set()

    def has(self, capability: str) -> bool:
        return False


def _obj_body(**kwargs):
    v = kwargs.get(DS_OBJECT)
    OBJ_SEEN.append(v)
    return {DS_OBJFACT: {"solved": v}}


def _obj_reduce_body(**kwargs):
    ordered = kwargs.get(DS_OBJFACTS)
    OBJ_REDUCER_SEEN.append(ordered)
    return {DS_GRIDFACT: {"grid_conclusion": ordered}}


def _grid_reduce_body(**kwargs):
    ordered = kwargs.get(DS_GRIDFACTS)
    GRID_REDUCER_SEEN.append(ordered)
    return {DS_CONCLUSION: {"conclusion": ordered}}


def _register(layer, obj_impl, *, session=None):
    collection_specs = {
        "s2.grids": dict(collection=True, member_ds=DS_GRID),
        "s2.grid": dict(collection=True, member_ds=DS_OBJECT),
        "s2.object_facts": dict(collection=True, member_ds=DS_OBJFACT),
        "s2.grid_facts": dict(collection=True, member_ds=DS_GRIDFACT),
    }
    names = (
        "s2.grids", "s2.grid", "s2.object", "s2.object_fact",
        "s2.object_facts", "s2.grid_fact", "s2.grid_facts", "s2.conclusion",
    )
    for name in names:
        extra = collection_specs.get(name, {})
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
            name="s2_object_solve", category=CATEGORY_DERIVATION,
            inputs=(DS_OBJECT,), outputs=(DS_OBJFACT,), implementation=obj_impl,
            description="object -> object_fact",
        ),
        session=session,
    )
    layer.register_capacity(
        Capacity(
            name="s2_object_reduce", category=CATEGORY_DERIVATION,
            inputs=(DS_OBJFACTS,), outputs=(DS_GRIDFACT,),
            implementation=_obj_reduce_body,
            description="object_facts -> grid_fact",
        ),
        session=session,
    )
    layer.register_capacity(
        Capacity(
            name="s2_grid_reduce", category=CATEGORY_DERIVATION,
            inputs=(DS_GRIDFACTS,), outputs=(DS_CONCLUSION,),
            implementation=_grid_reduce_body,
            description="grid_facts -> conclusion",
        ),
        session=session,
    )


def _nested_plan():
    """Outer map(grids) whose per-grid sub-plan = inner map(objects) + inner fold;
    then an outer fold over the grid facts."""
    inner_sub_plan = {
        "leaf_milestone_refs": ["mObjMap", "mObjFold"],
        "pipeline_refs": {"mObjMap": "pObjMap", "mObjFold": "pObjFold"},
        "milestone_specs": {
            "mObjMap": {
                "kind": "map", "collection_ds": DS_GRID, "member_ds": DS_OBJECT,
                "sub_target": DS_OBJFACT, "out_ds": DS_OBJFACTS,
            },
            "mObjFold": {
                "kind": "fold", "reducer_iri": CAP_OBJ_REDUCE, "in_ds": DS_OBJFACTS,
            },
        },
    }
    return PlanResult(
        plan_ref="plan:s2",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mGridMap", "mGridFold"],
        pipeline_refs={"mGridMap": "pGridMap", "mGridFold": "pGridFold"},
        milestone_specs={
            "mGridMap": {
                "kind": "map", "collection_ds": DS_GRIDS, "member_ds": DS_GRID,
                "sub_target": DS_GRIDFACT, "out_ds": DS_GRIDFACTS,
                "sub_plan": inner_sub_plan,
            },
            "mGridFold": {
                "kind": "fold", "reducer_iri": CAP_GRID_REDUCE, "in_ds": DS_GRIDFACTS,
            },
        },
    )


def _harness(obj_impl):
    sess = FakeSession()
    layer = CapacityLayer()
    _register(layer, obj_impl, session=sess)
    mm = MentalModel(session_id="s", user_id="u")
    disp = L4Dispatcher(layer, session=sess)
    writer = ChainArtifactWriter(mm, "t")
    request_run = writer.emit_request_run()
    return mm, disp, writer, request_run


# grids = [grid0, grid1]; each grid = [obj, obj]
GRID0 = [{"o": "00"}, {"o": "01"}]
GRID1 = [{"o": "10"}, {"o": "11"}]
SEED = {DS_GRIDS: [GRID0, GRID1]}


def test_map_in_map_double_folds_in_order_with_isolated_nested_refs():
    OBJ_SEEN.clear()
    OBJ_REDUCER_SEEN.clear()
    GRID_REDUCER_SEEN.clear()
    mm, disp, writer, request_run = _harness(_obj_body)
    graphs: list = []
    execution.run(
        disp, writer, _nested_plan(), request_run,
        mm=mm, run_scope="t", solve_seed=SEED, capacity_graphs=graphs,
    )
    # Double fan-out: every object ran, in outer-then-inner collection order.
    assert OBJ_SEEN == [{"o": "00"}, {"o": "01"}, {"o": "10"}, {"o": "11"}]
    # Inner fold ran once per grid, each over its grid's ordered object facts.
    assert OBJ_REDUCER_SEEN == [
        [{"solved": {"o": "00"}}, {"solved": {"o": "01"}}],
        [{"solved": {"o": "10"}}, {"solved": {"o": "11"}}],
    ]
    # Outer fold ran once over the two grids' facts, in order.
    assert GRID_REDUCER_SEEN == [[
        {"grid_conclusion": [{"solved": {"o": "00"}}, {"solved": {"o": "01"}}]},
        {"grid_conclusion": [{"solved": {"o": "10"}}, {"solved": {"o": "11"}}]},
    ]]
    # Provenance: 2 top milestones (map+fold) + per grid 2 (map+fold) x2 = 6.
    assert len(request_run.pipeline_runs) == 6
    # One grounding graph per innermost object member (4); folds dispatch, no graph.
    assert len(graphs) == 4
    # Core Slice-2 change: nested per-object grounding graphs carry DISTINCT role
    # tokens that ENCODE the nesting path (outer member m{g}, inner member m{o}),
    # so a nested run stays isolated + the tree is walkable by path.
    roles = {g.role for g in mm.capacity_mm.graphs.values()}
    expected = {
        run_graph_role("t", f"pipelinerun:t:0:m{g}:0:m{o}:0:r0")
        for g in (0, 1) for o in (0, 1)
    }
    assert expected <= roles          # all four nested paths present
    assert len(expected) == 4         # and they are genuinely distinct


def test_inner_member_abort_propagates_unretried_and_skips_rest():
    OBJ_SEEN.clear()
    OBJ_REDUCER_SEEN.clear()
    GRID_REDUCER_SEEN.clear()

    def _fail_obj_01(**kwargs):
        v = kwargs.get(DS_OBJECT)
        OBJ_SEEN.append(v)
        if v == {"o": "01"}:
            raise RuntimeError("object 01 load failure")
        return {DS_OBJFACT: {"solved": v}}

    mm, disp, writer, request_run = _harness(_fail_obj_01)
    with pytest.raises(execution.MemberAbortError) as ei:
        execution.run(
            disp, writer, _nested_plan(), request_run,
            mm=mm, run_scope="t", solve_seed=SEED, capacity_graphs=[],
        )
    # The escaping abort names the innermost failing member (inner map index 1).
    assert ei.value.member_index == 1
    # Object 01 retried to the cap; grid1 never entered; no fold at any level ran.
    assert OBJ_SEEN.count({"o": "01"}) == execution.MEMBER_RETRY_CAP
    assert {"o": "10"} not in OBJ_SEEN and {"o": "11"} not in OBJ_SEEN
    assert OBJ_REDUCER_SEEN == []
    assert GRID_REDUCER_SEEN == []


def test_retry_then_succeed_inside_nested_map():
    OBJ_SEEN.clear()
    OBJ_REDUCER_SEEN.clear()
    GRID_REDUCER_SEEN.clear()
    ATTEMPTS.clear()

    def _fail_obj_10_once(**kwargs):
        v = kwargs.get(DS_OBJECT)
        key = v["o"]
        ATTEMPTS[key] = ATTEMPTS.get(key, 0) + 1
        OBJ_SEEN.append(v)
        if v == {"o": "10"} and ATTEMPTS[key] == 1:
            raise RuntimeError("transient inner load failure")
        return {DS_OBJFACT: {"solved": v}}

    mm, disp, writer, request_run = _harness(_fail_obj_10_once)
    execution.run(
        disp, writer, _nested_plan(), request_run,
        mm=mm, run_scope="t", solve_seed=SEED, capacity_graphs=[],
    )
    # Inner member retried once within the cap, then the whole nest completed.
    assert ATTEMPTS["10"] == 2
    assert GRID_REDUCER_SEEN == [[
        {"grid_conclusion": [{"solved": {"o": "00"}}, {"solved": {"o": "01"}}]},
        {"grid_conclusion": [{"solved": {"o": "10"}}, {"solved": {"o": "11"}}]},
    ]]
