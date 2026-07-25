"""Collection-iteration Slice 1a — the cross-milestone value bus.

Before this slice ``execution.run`` ran each leaf's pipeline in its own
blackboard seeded identically from ``solve_seed`` and discarded the outputs, so
a value produced in one milestone could never reach a later one — every solve
was single-leaf. Slice 1a threads a run-scoped, attempt-scoped blackboard across
milestones: a leaf seeds from it (filtered to its pipeline's ``start_datastates``)
and merges its outputs back, so a downstream stage consumes what an upstream
stage produced. ``PlanResult.leaf_targets`` names per-leaf endpoints for such a
chain. No map/fold fan-out yet (that is Slice 1b).

These tests exercise the bus with a synthetic two-stage plan
(``raw_task -> raw_grids`` then ``raw_grids -> answer``) over real capacities —
no Falkor. The single-leaf Step-5 path is covered by
``tests/phase_48/test_step5_solve_execution.py`` and must stay green (the
fallback to the plan-global ``solve_target`` is unchanged).
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION,
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_DATASTATE_INSTANCE_TYPE,
    capacity_iri,
    datastate_iri,
)

from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

DS_RAW = datastate_iri("s1a.raw_task")
DS_GRIDS = datastate_iri("s1a.raw_grids")
DS_ANS = datastate_iri("s1a.answer")

CAP_A = capacity_iri(CATEGORY_DERIVATION, "s1a_fetch")  # raw_task -> raw_grids
CAP_B = capacity_iri(CATEGORY_DERIVATION, "s1a_solve")  # raw_grids -> answer

#: Records every ``raw_grids`` value the downstream (stage-B) capacity receives,
#: so a test can prove it arrived from the upstream (stage-A) output rather than
#: from the seed (the seed carries only ``raw_task``).
SEEN_GRIDS: list = []


class FakeSession:
    def __init__(self, user_id="u"):
        self.session_id = "s"
        self.user_id = user_id
        self.actor_role = "user"
        self.capabilities = set()

    def has(self, capability: str) -> bool:
        return False


def _stage_a_body(**kwargs):
    # Derive raw_grids from the seeded raw_task, so a correct thread of BOTH the
    # seed (into A) and A's output (into B) is observable end to end.
    return {DS_GRIDS: {"grids_from": kwargs.get(DS_RAW)}}


def _stage_b_body(**kwargs):
    SEEN_GRIDS.append(kwargs.get(DS_GRIDS))
    return {DS_ANS: {"ans_from": kwargs.get(DS_GRIDS)}}


def _register_chain(layer, *, session=None):
    for name in ("s1a.raw_task", "s1a.raw_grids", "s1a.answer"):
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=name,
                provenance_category=CATEGORY_DERIVATION,
            ),
            session=session,
            allow_new_realm=True,
        )
    layer.register_capacity(
        Capacity(
            name="s1a_fetch", category=CATEGORY_DERIVATION,
            inputs=(DS_RAW,), outputs=(DS_GRIDS,),
            implementation=_stage_a_body,
            description="stage A: raw_task -> raw_grids",
        ),
        session=session,
    )
    layer.register_capacity(
        Capacity(
            name="s1a_solve", category=CATEGORY_DERIVATION,
            inputs=(DS_GRIDS,), outputs=(DS_ANS,),
            implementation=_stage_b_body,
            description="stage B: raw_grids -> answer",
        ),
        session=session,
    )


def _all_run_graphs(mm):
    return [
        g for g in mm.capacity_mm.graphs.values()
        if g.role.startswith("capacity:run:")
    ]


def _two_stage_plan():
    return PlanResult(
        plan_ref="plan:1",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mA", "mB"],
        pipeline_refs={"mA": "pA", "mB": "pB"},
        solve_target=None,
        leaf_targets={
            "mA": {"start_datastate": DS_RAW, "target_datastate": DS_GRIDS},
            "mB": {"start_datastate": DS_GRIDS, "target_datastate": DS_ANS},
        },
    )


def test_value_bus_threads_produced_value_to_downstream_leaf():
    SEEN_GRIDS.clear()
    sess = FakeSession()
    layer = CapacityLayer()
    _register_chain(layer, session=sess)
    mm = MentalModel(session_id="s", user_id="u")
    disp = L4Dispatcher(layer, session=sess)
    writer = ChainArtifactWriter(mm, "t1")
    task_run = writer.emit_task_run()

    graphs: list = []
    execution.run(
        disp, writer, _two_stage_plan(), task_run,
        mm=mm, run_scope="t1",
        solve_seed={DS_RAW: {"seed": 1}},  # ONLY raw_task is seeded
        capacity_graphs=graphs,
    )

    # Stage B received exactly the value stage A produced from the seed — proof
    # the value crossed the milestone boundary (raw_grids was never in the seed).
    assert SEEN_GRIDS == [{"grids_from": {"seed": 1}}]

    # Both leaves ran for real (two isolated per-run grounding graphs collected).
    assert len(_all_run_graphs(mm)) == 2
    assert len(graphs) == 2
    assert len(task_run.pipeline_runs) == 2

    # Stage B's grounding graph carries the threaded raw_grids as its seeded root
    # plus the produced answer.
    b_graph = graphs[1]
    grid_roots = [
        n.value for n in b_graph.nodes.values()
        if n.type_name == NODE_TYPE_DATASTATE_INSTANCE
        and n.properties.get(PROP_DATASTATE_INSTANCE_TYPE) == DS_GRIDS
    ]
    assert grid_roots == [{"grids_from": {"seed": 1}}]
    ans = [
        n.value for n in b_graph.nodes.values()
        if n.type_name == NODE_TYPE_DATASTATE_INSTANCE
        and n.properties.get(PROP_DATASTATE_INSTANCE_TYPE) == DS_ANS
    ]
    assert ans == [{"ans_from": {"grids_from": {"seed": 1}}}]


def test_blackboard_is_attempt_scoped_fresh_per_run():
    """Each ``execution.run`` call builds its own blackboard from ``solve_seed``,
    so a re-run (the replan shape) threads the CURRENT seed's values, never a
    stale carry-over from a prior call."""
    SEEN_GRIDS.clear()
    sess = FakeSession()
    layer = CapacityLayer()
    _register_chain(layer, session=sess)
    mm = MentalModel(session_id="s", user_id="u")
    disp = L4Dispatcher(layer, session=sess)

    for attempt, seed in enumerate([{"seed": "first"}, {"seed": "second"}]):
        writer = ChainArtifactWriter(mm, f"t{attempt}")
        task_run = writer.emit_task_run()
        execution.run(
            disp, writer, _two_stage_plan(), task_run,
            mm=mm, run_scope=f"t{attempt}",
            solve_seed={DS_RAW: seed}, capacity_graphs=[],
            run_attempt=attempt,
        )

    assert SEEN_GRIDS == [
        {"grids_from": {"seed": "first"}},
        {"grids_from": {"seed": "second"}},
    ]
