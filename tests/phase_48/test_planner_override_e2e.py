"""Collection-iteration — a REAL registered ``derive_initial_plan`` override
emits the map/fold ``milestones`` shape, resolves through a REAL ``L4Dispatcher``
in ``plan_construction.build``, and drives the executor's fan-out + fold.

Closes the coverage gap left by ``test_plan_milestones_build.py``: its
end-to-end test feeds ``milestones`` via a *fake* planner-dispatcher, so no test
ever proved that a brain-registered planner override
(``register_capacity(..., if_exists="upsert")`` -> ``_declarations`` swap) is
what a real dispatch resolves. That override is the exact path a consumer brain
uses to emit map/fold plans (ADR-0199 / locked decision 3); until now it was
never exercised end-to-end. This test registers the v0 builtin
``derive_initial_plan`` and then upsert-overrides it with a milestones-emitting
implementation (the historically-fragile swap path, ADR-0156 §amendment-1),
proving the override -> real-dispatch -> ``build`` -> executor chain.
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION,
    CATEGORY_PLANNING,
    capacity_iri,
    datastate_iri,
)
from mindsos_capacity.builtins.planning_v0 import (
    DS_MAPPING_RESULT,
    DS_PLAN,
    build_derive_initial_plan,
    planning_datastates,
)

from mindsos_intelligence import execution, plan_construction
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel

COLL = datastate_iri("ov.coll")
MEMBER = datastate_iri("ov.mem")
SUB = datastate_iri("ov.sub")
OUT = datastate_iri("ov.out")
AGG = datastate_iri("ov.agg")
REDUCE = capacity_iri(CATEGORY_DERIVATION, "ov_reduce")

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
    v = kw.get(MEMBER)
    _MEMBER_SEEN.append(v)
    return {SUB: {"solved": v}}


def _reduce_body(**kw):
    ordered = kw.get(OUT)
    _REDUCER_SEEN.append(ordered)
    return {AGG: {"conclusion": ordered}}


def _register_domain(layer, session):
    """The per-member capacity + reducer + their DataStates (mirrors the
    real-capacity harness in test_plan_milestones_build.py)."""
    specs = {
        "ov.coll": dict(collection=True, member_ds=MEMBER),
        "ov.out": dict(collection=True, member_ds=SUB),
    }
    for name in ("ov.coll", "ov.mem", "ov.sub", "ov.out", "ov.agg"):
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
            name="ov_member", category=CATEGORY_DERIVATION,
            inputs=(MEMBER,), outputs=(SUB,), implementation=_member_body,
            description="member: mem -> sub",
        ),
        session=session,
    )
    layer.register_capacity(
        Capacity(
            name="ov_reduce", category=CATEGORY_DERIVATION,
            inputs=(OUT,), outputs=(AGG,), implementation=_reduce_body,
            description="reducer: out -> agg",
        ),
        session=session,
    )


def test_registered_planner_override_drives_map_fold_end_to_end():
    _MEMBER_SEEN.clear()
    _REDUCER_SEEN.clear()
    map_spec = {
        "kind": "map", "collection_ds": COLL, "member_ds": MEMBER,
        "sub_target": SUB, "out_ds": OUT,
    }
    fold_spec = {"kind": "fold", "reducer_iri": REDUCE, "in_ds": OUT}

    sess = _FakeSession()
    layer = CapacityLayer()
    _register_domain(layer, sess)

    # Planning substrate: the DataStates + the opt-in v0 builtin
    # derive_initial_plan (what a brain installs before overriding it).
    for ds in planning_datastates():
        layer.register_datastate(ds, session=sess, allow_new_realm=True)
    layer.register_capacity(build_derive_initial_plan(), session=sess)

    # The exact never-before-tested link: a brain overrides the planner impl in
    # place (same IRI, if_exists="upsert" -> _declarations swap) so that a REAL
    # dispatch of derive_initial_plan returns a map/fold milestones shape.
    def _override(**kw):
        return {DS_PLAN: {"milestones": [{"spec": map_spec}, {"spec": fold_spec}]}}

    layer.register_capacity(
        Capacity(
            name="derive_initial_plan", category=CATEGORY_PLANNING,
            inputs=(DS_MAPPING_RESULT,), outputs=(DS_PLAN,),
            implementation=_override,
            description="brain override: emits map/fold milestones",
        ),
        session=sess, if_exists="upsert",
    )

    disp = L4Dispatcher(layer, session=sess)
    mm = MentalModel(session_id="s", user_id="u")
    writer = ChainArtifactWriter(mm, "t")

    # build() dispatches derive_initial_plan through the REAL dispatcher; the
    # upserted override must be what resolves and its milestones must thread in.
    plan_result = plan_construction.build(
        disp, writer, "mr:1", "rp:1", resolved_reference="ref"
    )
    assert plan_result.milestone_specs is not None, (
        "the upsert-overridden planner's milestones did not reach PlanResult"
    )
    specs_in_order = [
        plan_result.milestone_specs[r] for r in plan_result.leaf_milestone_refs
    ]
    assert specs_in_order == [map_spec, fold_spec]

    # And the built plan drives the real map/fold executor end-to-end.
    request_run = writer.emit_request_run()
    graphs: list = []
    execution.run(
        disp, writer, plan_result, request_run,
        mm=mm, run_scope="t",
        solve_seed={COLL: [{"m": 0}, {"m": 1}, {"m": 2}]},
        capacity_graphs=graphs,
    )
    # Fan-out in collection order; fold received the ordered member outputs.
    assert _MEMBER_SEEN == [{"m": 0}, {"m": 1}, {"m": 2}]
    assert _REDUCER_SEEN == [[
        {"solved": {"m": 0}}, {"solved": {"m": 1}}, {"solved": {"m": 2}},
    ]]
    assert len(request_run.pipeline_runs) == 2  # map + fold
