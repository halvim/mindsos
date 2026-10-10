"""A start value names where it came from (``mindsos_llm`` plan I-19, gate 1).

A request is many run graphs — one per milestone, per map member and per fold
— and values pass between them on an in-memory blackboard, so the receiving
graph shows a value an earlier run PRODUCED as a parentless start, exactly like
one the caller handed in. ADR-0201 amendment 4 tells a renderer that such a
start "is a premise the run was given"; for a value an earlier run computed —
possibly from a model reading — that is false, and nothing in the stored
Episode lets anyone tell the two apart (plan §6, 2026-10-09, finding 7).

Gate 1's claim, over the three places ``execution`` seeds a run (a leaf, a map
member, a fold), nested sub-plans and a targeted re-run included: every start
of a grounded run is recorded in the run manifest's ``start_origins`` as
``given`` (handed to ``execution.run`` by its caller) or as ``produced`` by
named instances in named run graphs. A manifest minted by a caller that records
no origins carries no key at all — absence means *not recorded*, never *given*
(plan R50; ADR-0201 amendment 5's key-presence rule).

The persisted shape is spelled as literals on purpose: it is a contract on
stored Episodes, and renaming a constant must not silently change it.
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION,
    EDGE_PRODUCES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    NODE_TYPE_RUN_MANIFEST,
    PROP_CAPACITY_INSTANCE_TYPE,
    PROP_DATASTATE_INSTANCE_TYPE,
    capacity_iri,
    datastate_iri,
)
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline
from mindsos_intelligence.plan_construction import PlanResult

KEY = "start_origins"
GIVEN = {"kind": "given"}

DS_RAW = datastate_iri("sno.raw")
DS_COLL = datastate_iri("sno.parts")
DS_CTX = datastate_iri("sno.context")
DS_MEMBER = datastate_iri("sno.part")
DS_MID = datastate_iri("sno.part_read")
DS_SUB = datastate_iri("sno.part_verdict")
DS_OUT = datastate_iri("sno.part_verdicts")
DS_AGG = datastate_iri("sno.conclusion")
DS_REPORT = datastate_iri("sno.report")

CAP_SPLIT = capacity_iri(CATEGORY_DERIVATION, "sno_split")
CAP_CTX = capacity_iri(CATEGORY_DERIVATION, "sno_context")
CAP_DECIDE = capacity_iri(CATEGORY_DERIVATION, "sno_decide")
CAP_READ = capacity_iri(CATEGORY_DERIVATION, "sno_read_part")
CAP_JUDGE = capacity_iri(CATEGORY_DERIVATION, "sno_judge_part")
CAP_CONCLUDE = capacity_iri(CATEGORY_DERIVATION, "sno_conclude")
CAP_REPORT = capacity_iri(CATEGORY_DERIVATION, "sno_report")

COLLECTIONS = {
    "sno.parts": dict(collection=True, member_ds=DS_MEMBER),
    "sno.part_verdicts": dict(collection=True, member_ds=DS_SUB),
}


class FakeSession:
    session_id = "s"
    user_id = "u"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability: str) -> bool:
        return False


def _harness(*, with_context: bool):
    session = FakeSession()
    layer = CapacityLayer()
    for name in (
        "sno.raw", "sno.parts", "sno.context", "sno.part", "sno.part_read",
        "sno.part_verdict", "sno.part_verdicts", "sno.conclusion", "sno.report",
    ):
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=name.replace("sno.", "the ").replace("_", " "),
                provenance_category=CATEGORY_DERIVATION,
                **COLLECTIONS.get(name, {}),
            ),
            session=session,
            allow_new_realm=True,
        )

    def cap(name, inputs, outputs, body):
        layer.register_capacity(
            Capacity(
                name=name, category=CATEGORY_DERIVATION,
                inputs=inputs, outputs=outputs, implementation=body,
                description=name.replace("_", " "),
            ),
            session=session,
        )

    cap("sno_split", (DS_RAW,), (DS_COLL,),
        lambda **kw: {DS_COLL: list(kw[DS_RAW])})
    cap("sno_context", (DS_RAW,), (DS_CTX,),
        lambda **kw: {DS_CTX: len(kw[DS_RAW])})
    if with_context:
        cap("sno_decide", (DS_MEMBER, DS_CTX), (DS_SUB,),
            lambda **kw: {DS_SUB: [kw[DS_MEMBER], kw[DS_CTX]]})
    else:
        cap("sno_read_part", (DS_MEMBER,), (DS_MID,),
            lambda **kw: {DS_MID: f"read {kw[DS_MEMBER]}"})
        cap("sno_judge_part", (DS_MID,), (DS_SUB,),
            lambda **kw: {DS_SUB: f"judged {kw[DS_MID]}"})
    cap("sno_conclude", (DS_OUT,), (DS_AGG,),
        lambda **kw: {DS_AGG: list(kw[DS_OUT])})
    cap("sno_report", (DS_AGG,), (DS_REPORT,),
        lambda **kw: {DS_REPORT: {"of": kw[DS_AGG]}})
    mm = MentalModel(session_id="s", user_id="u")
    dispatcher = L4Dispatcher(layer, session=session)
    writer = ChainArtifactWriter(mm, "t")
    return mm, dispatcher, writer, writer.emit_request_run()


def _chain_plan() -> PlanResult:
    """split and context from the caller's value; map with context shared;
    fold; then a leaf over the fold's conclusion."""
    refs = ["mSplit", "mCtx", "mMap", "mFold", "mReport"]
    return PlanResult(
        plan_ref="plan:sno",
        root_milestone_ref="m0",
        leaf_milestone_refs=refs,
        pipeline_refs={r: f"p{r}" for r in refs},
        leaf_targets={
            "mSplit": {"start_datastate": DS_RAW, "target_datastate": DS_COLL},
            "mCtx": {"start_datastate": DS_RAW, "target_datastate": DS_CTX},
            "mReport": {"start_datastate": DS_AGG, "target_datastate": DS_REPORT},
        },
        milestone_specs={
            "mMap": {
                "kind": "map", "collection_ds": DS_COLL, "member_ds": DS_MEMBER,
                "sub_target": DS_SUB, "out_ds": DS_OUT,
                "shared_inputs": [DS_CTX],
            },
            "mFold": {"kind": "fold", "reducer_iri": CAP_CONCLUDE, "in_ds": DS_OUT},
        },
    )


def _sub_plan_plan() -> PlanResult:
    """A caller-given collection; each member runs a two-leaf sub-plan."""
    sub_plan = {
        "leaf_milestone_refs": ["s0", "s1"],
        "pipeline_refs": {"s0": "pS0", "s1": "pS1"},
        "milestone_specs": {},
        "leaf_targets": {
            "s0": {"start_datastate": DS_MEMBER, "target_datastate": DS_MID},
            "s1": {"start_datastate": DS_MID, "target_datastate": DS_SUB},
        },
    }
    return PlanResult(
        plan_ref="plan:sno-sub",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mMap", "mFold"],
        pipeline_refs={"mMap": "pMap", "mFold": "pFold"},
        milestone_specs={
            "mMap": {
                "kind": "map", "collection_ds": DS_COLL, "member_ds": DS_MEMBER,
                "sub_target": DS_SUB, "out_ds": DS_OUT, "sub_plan": sub_plan,
            },
            "mFold": {"kind": "fold", "reducer_iri": CAP_CONCLUDE, "in_ds": DS_OUT},
        },
    )


def _flat_map_plan() -> PlanResult:
    return PlanResult(
        plan_ref="plan:sno-flat",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mMap", "mFold"],
        pipeline_refs={"mMap": "pMap", "mFold": "pFold"},
        milestone_specs={
            "mMap": {
                "kind": "map", "collection_ds": DS_COLL, "member_ds": DS_MEMBER,
                "sub_target": DS_SUB, "out_ds": DS_OUT,
            },
            "mFold": {"kind": "fold", "reducer_iri": CAP_CONCLUDE, "in_ds": DS_OUT},
        },
    )


def _nodes(graph, type_name):
    return [n for n in graph.nodes.values() if n.type_name == type_name]


def _ran(graph, cap):
    return any(
        n.properties.get(PROP_CAPACITY_INSTANCE_TYPE) == cap
        for n in _nodes(graph, NODE_TYPE_CAPACITY_INSTANCE)
    )


def _graphs_running(graphs, cap):
    return [g for g in graphs if _ran(g, cap)]


def _one_graph_running(graphs, cap):
    found = _graphs_running(graphs, cap)
    assert len(found) == 1, f"{cap}: {len(found)} graphs"
    return found[0]


def _origins(graph):
    manifests = _nodes(graph, NODE_TYPE_RUN_MANIFEST)
    assert len(manifests) == 1
    return manifests[0].value.get(KEY)


def _produced(graph, ds):
    """The one instance of ``ds`` a capacity in ``graph`` PRODUCED."""
    found = [
        e.target.node_id for e in graph.edges.values()
        if e.type_name == EDGE_PRODUCES
        and e.source.type_name == NODE_TYPE_CAPACITY_INSTANCE
        and e.target.type_name == NODE_TYPE_DATASTATE_INSTANCE
        and (e.target.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE) == ds
    ]
    assert len(found) == 1, f"{ds}: {len(found)} produced instances"
    return {"graph_id": graph.graph_id, "instance_id": found[0]}


def _by(*refs):
    return {"kind": "produced", "by": list(refs)}


def _run(plan, seed, harness, *, graphs=None, blackboard=None,
         targeted=None, run_attempt=0):
    mm, dispatcher, writer, request_run = harness
    graphs = graphs if graphs is not None else []
    execution.run(
        dispatcher, writer, plan, request_run,
        mm=mm, run_scope="t", solve_seed=seed, capacity_graphs=graphs,
        blackboard=blackboard, targeted=targeted, run_attempt=run_attempt,
    )
    return graphs


def _chain():
    return _run(_chain_plan(), {DS_RAW: "abc"}, _harness(with_context=True))


def test_a_start_the_caller_handed_in_is_given():
    graphs = _chain()
    assert _origins(_one_graph_running(graphs, CAP_SPLIT)) == {DS_RAW: GIVEN}
    assert _origins(_one_graph_running(graphs, CAP_CTX)) == {DS_RAW: GIVEN}


def test_a_member_and_its_shared_input_name_the_runs_that_produced_them():
    graphs = _chain()
    split = _one_graph_running(graphs, CAP_SPLIT)
    ctx = _one_graph_running(graphs, CAP_CTX)
    members = _graphs_running(graphs, CAP_DECIDE)
    assert len(members) == 3
    for member in members:
        assert _origins(member) == {
            DS_MEMBER: _by(_produced(split, DS_COLL)),
            DS_CTX: _by(_produced(ctx, DS_CTX)),
        }


def test_the_fold_start_names_every_member_that_produced_it_in_order():
    graphs = _chain()
    members = _graphs_running(graphs, CAP_DECIDE)
    fold = _one_graph_running(graphs, CAP_CONCLUDE)
    assert _origins(fold) == {
        DS_OUT: _by(*[_produced(m, DS_SUB) for m in members]),
    }


def test_a_leaf_after_the_fold_names_the_fold():
    graphs = _chain()
    fold = _one_graph_running(graphs, CAP_CONCLUDE)
    report = _one_graph_running(graphs, CAP_REPORT)
    assert _origins(report) == {DS_AGG: _by(_produced(fold, DS_AGG))}


def test_inside_a_sub_plan_each_start_names_its_origin():
    graphs = _run(
        _sub_plan_plan(), {DS_COLL: ["p", "q"]}, _harness(with_context=False),
    )
    readers = _graphs_running(graphs, CAP_READ)
    judges = _graphs_running(graphs, CAP_JUDGE)
    assert len(readers) == len(judges) == 2
    for reader, judge in zip(readers, judges):
        assert _origins(reader) == {DS_MEMBER: GIVEN}
        assert _origins(judge) == {DS_MID: _by(_produced(reader, DS_MID))}
    fold = _one_graph_running(graphs, CAP_CONCLUDE)
    assert _origins(fold) == {
        DS_OUT: _by(*[_produced(j, DS_SUB) for j in judges]),
    }


def test_a_targeted_rerun_splices_the_fresh_member_into_the_fold_origin():
    harness = _harness(with_context=False)
    bb: dict = {DS_COLL: ["p", "q", "r"]}
    graphs = _run(_flat_map_plan(), {DS_COLL: ["p", "q", "r"]}, harness,
                  blackboard=bb)
    first = _graphs_running(graphs, CAP_READ)
    before = len(graphs)
    graphs = _run(_flat_map_plan(), {DS_COLL: ["p", "q", "r"]}, harness,
                  graphs=graphs, blackboard=bb, targeted=(0, 1), run_attempt=1)
    fresh = _one_graph_running(graphs[before:], CAP_READ)
    fold = _one_graph_running(graphs[before:], CAP_CONCLUDE)
    assert _origins(fold) == {
        DS_OUT: _by(
            _produced(first[0], DS_SUB),
            _produced(fresh, DS_SUB),
            _produced(first[2], DS_SUB),
        ),
    }


def test_a_manifest_minted_without_origins_carries_no_key():
    """Absent means NOT RECORDED, never given (R50): a direct caller of
    ``execute_pipeline`` that passes no origins leaves the key out."""
    mm, dispatcher, _, _ = _harness(with_context=True)
    pipeline = execution._compose_pipeline(
        dispatcher, (DS_RAW,), DS_COLL, execution.FINDER_BFS,
    ).pipeline
    result = execute_pipeline(
        dispatcher, pipeline, {DS_RAW: "ab"},
        request_id="direct", mm=mm, pipeline_run_ref="pipelinerun:direct",
    )
    assert result.success
    manifest = _nodes(result.capacity_graph, NODE_TYPE_RUN_MANIFEST)[0]
    assert KEY not in manifest.value
