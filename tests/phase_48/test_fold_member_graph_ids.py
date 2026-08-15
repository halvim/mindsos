"""The fold manifest carries the member correlation (ADR-0201 amendment 5).

Which member produced which verdict used to stay "structural via the
ref-path", and the shipped demo renderer correlated by full verdict-value
equality against the fold's seeded list. Shape (a) (ADR-0209) makes the
breaking case legal: two members that both refuse in-band may carry
IDENTICAL values, while their pages must differ — demo finding N-F2. The fix
is the amendment's `member_graph_ids`: the fold run's manifest carries the
ordered `graph_id` of each member's grounding graph, so position *i* of the
seeded list correlates to member graph *i* structurally.

Harness is `test_fold_grounding`'s (same registrations, same plan shape) —
duplicated per house style, not imported across test modules.
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION,
    MANIFEST_MEMBER_GRAPH_IDS,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_RUN_MANIFEST,
    PROP_CAPACITY_INSTANCE_TYPE,
    capacity_iri,
    datastate_iri,
)
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

DS_COLL = datastate_iri("fmi.exposures")
DS_MEMBER = datastate_iri("fmi.exposure")
DS_SUB = datastate_iri("fmi.verdict")
DS_OUT = datastate_iri("fmi.verdicts")
DS_AGG = datastate_iri("fmi.claim_conclusion")

CAP_SOLVE = capacity_iri(CATEGORY_DERIVATION, "fmi_decide_one")
CAP_REDUCE = capacity_iri(CATEGORY_DERIVATION, "fmi_conclude")

DESCRIPTIONS = {
    "fmi.exposures": "the exposures the claim was split into",
    "fmi.exposure": "one exposure, as filed",
    "fmi.verdict": "what was decided about one exposure",
    "fmi.verdicts": "each exposure's verdict, in order",
    "fmi.claim_conclusion": "what the claim's verdicts add up to",
}
COLLECTIONS = {
    "fmi.exposures": dict(collection=True, member_ds=DS_MEMBER),
    "fmi.verdicts": dict(collection=True, member_ds=DS_SUB),
}


class FakeSession:
    session_id = "s"
    user_id = "u"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability: str) -> bool:
        return False


def _member_body(**kwargs):
    return {DS_SUB: {"verdict": kwargs.get(DS_MEMBER)}}


def _reduce_body(**kwargs):
    return {DS_AGG: {"conclusion": kwargs.get(DS_OUT)}}


def _harness():
    session = FakeSession()
    layer = CapacityLayer()
    for name, description in DESCRIPTIONS.items():
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=description,
                provenance_category=CATEGORY_DERIVATION,
                **COLLECTIONS.get(name, {}),
            ),
            session=session,
            allow_new_realm=True,
        )
    layer.register_capacity(
        Capacity(
            name="fmi_decide_one",
            category=CATEGORY_DERIVATION,
            inputs=(DS_MEMBER,),
            outputs=(DS_SUB,),
            implementation=_member_body,
            description="one exposure -> its verdict",
        ),
        session=session,
    )
    layer.register_capacity(
        Capacity(
            name="fmi_conclude",
            category=CATEGORY_DERIVATION,
            inputs=(DS_OUT,),
            outputs=(DS_AGG,),
            implementation=_reduce_body,
            description="the ordered verdicts -> the claim conclusion",
            printable_phrase="concluding the claim from its exposure verdicts",
        ),
        session=session,
    )
    mm = MentalModel(session_id="s", user_id="u")
    dispatcher = L4Dispatcher(layer, session=session)
    writer = ChainArtifactWriter(mm, "t")
    return mm, dispatcher, writer, writer.emit_request_run()


def _plan(sub_plan=None) -> PlanResult:
    map_spec = {
        "kind": "map", "collection_ds": DS_COLL, "member_ds": DS_MEMBER,
        "sub_target": DS_SUB, "out_ds": DS_OUT,
    }
    if sub_plan is not None:
        map_spec["sub_plan"] = sub_plan
    return PlanResult(
        plan_ref="plan:fmi",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mMap", "mFold"],
        pipeline_refs={"mMap": "pMap", "mFold": "pFold"},
        milestone_specs={
            "mMap": map_spec,
            "mFold": {"kind": "fold", "reducer_iri": CAP_REDUCE, "in_ds": DS_OUT},
        },
    )


def _nodes(graph, type_name):
    return [n for n in graph.nodes.values() if n.type_name == type_name]


def _is_member_graph(graph):
    return any(
        n.properties.get(PROP_CAPACITY_INSTANCE_TYPE) == CAP_SOLVE
        for n in _nodes(graph, NODE_TYPE_CAPACITY_INSTANCE)
    )


def _fold_graph(graphs):
    matches = [
        g for g in graphs
        if any(
            n.properties.get(PROP_CAPACITY_INSTANCE_TYPE) == CAP_REDUCE
            for n in _nodes(g, NODE_TYPE_CAPACITY_INSTANCE)
        )
    ]
    assert len(matches) == 1
    return matches[0]


def _manifest_value(graph):
    manifests = _nodes(graph, NODE_TYPE_RUN_MANIFEST)
    assert len(manifests) == 1
    return manifests[0].value


def _run(members, *, sub_plan=None, blackboard=None, graphs=None,
         targeted=None, run_attempt=0, harness=None):
    mm, dispatcher, writer, request_run = harness or _harness()
    graphs = graphs if graphs is not None else []
    execution.run(
        dispatcher, writer, _plan(sub_plan), request_run,
        mm=mm, solve_seed={DS_COLL: list(members)},
        capacity_graphs=graphs, blackboard=blackboard,
        targeted=targeted, run_attempt=run_attempt,
    )
    return graphs, (mm, dispatcher, writer, request_run)


# ── the field itself ──────────────────────────────────────────────────


def test_the_fold_manifest_carries_the_member_graph_ids_in_member_order():
    """Position i of the fold's seeded list <-> member_graph_ids[i]. The
    member graphs are appended in member order by the map; the manifest list
    must be exactly that sequence — order, not just set."""
    graphs, _ = _run(["e0", "e1", "e2"])
    member_ids = [g.graph_id for g in graphs if _is_member_graph(g)]
    assert len(member_ids) == 3
    manifest_ids = _manifest_value(_fold_graph(graphs))[MANIFEST_MEMBER_GRAPH_IDS]
    assert manifest_ids == member_ids


def test_the_fold_graph_itself_is_not_in_the_member_ids():
    graphs, _ = _run(["e0", "e1"])
    fold = _fold_graph(graphs)
    assert fold.graph_id not in _manifest_value(fold)[MANIFEST_MEMBER_GRAPH_IDS]


def test_member_and_leaf_manifests_carry_no_member_graph_ids_key():
    """The key is a fold fact. ABSENT elsewhere — not present-and-empty:
    absence is how a reader tells 'not a fold' from 'a fold over nothing'."""
    graphs, _ = _run(["e0", "e1"])
    for graph in graphs:
        if _is_member_graph(graph):
            assert MANIFEST_MEMBER_GRAPH_IDS not in _manifest_value(graph)


def test_a_targeted_rerun_splices_the_fresh_member_id_in_place():
    """Slice 3b: the retained id list splices exactly as the retained outputs
    do — the re-run member's fresh graph replaces its prior id, untargeted
    siblings keep theirs, order intact."""
    harness = _harness()
    bb: dict = {DS_COLL: ["e0", "e1", "e2"]}
    graphs, harness = _run(
        ["e0", "e1", "e2"], blackboard=bb, harness=harness,
    )
    first_ids = list(
        _manifest_value(_fold_graph(graphs))[MANIFEST_MEMBER_GRAPH_IDS]
    )
    before = len(graphs)
    graphs, _ = _run(
        ["e0", "e1", "e2"], blackboard=bb, graphs=graphs,
        targeted=(0, 1), run_attempt=1, harness=harness,
    )
    new_graphs = graphs[before:]
    new_member_ids = [g.graph_id for g in new_graphs if _is_member_graph(g)]
    assert len(new_member_ids) == 1
    second_ids = _manifest_value(_fold_graph(new_graphs))[
        MANIFEST_MEMBER_GRAPH_IDS
    ]
    assert second_ids == [first_ids[0], new_member_ids[0], first_ids[2]]
    assert second_ids != first_ids


def test_a_sub_plan_members_id_is_the_graph_that_produced_its_sub_target():
    """ADR-0209 D3: a sub-plan member's id is the run that PRODUCED its
    sub_target — read off the graphs (a PRODUCES edge into a
    DataStateInstance of that type), never off a ref-path."""
    sub_plan = {
        "leaf_milestone_refs": ["s0"],
        "pipeline_refs": {"s0": "pS"},
        "milestone_specs": {},
        "leaf_targets": {
            "s0": {"start_datastate": DS_MEMBER, "target_datastate": DS_SUB},
        },
    }
    graphs, _ = _run(["e0", "e1"], sub_plan=sub_plan)
    producer_ids = [
        g.graph_id
        for g in graphs
        if execution._produced_graph_id([g], DS_SUB) == g.graph_id
    ]
    assert len(producer_ids) == 2
    manifest_ids = _manifest_value(_fold_graph(graphs))[MANIFEST_MEMBER_GRAPH_IDS]
    assert manifest_ids == producer_ids
