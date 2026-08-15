"""An empty fold domain never reaches the reducer (ADR-0201 amendment 5).

The shipped behaviour this replaces: a claim with ZERO exposures ran end to
end and concluded payable-from-nothing — the map wrote ``[]`` to ``out_ds``,
nothing in core refused, and the reducer received an empty list as
legitimate input (`core-empty-fold-domain`, demo-critical sweep F1). Owner
ruling: at the FOLD, not per reducer — a consumer's reducer refusing is one
consumer patching itself, and the next consumer reintroduces the hole.

The stop is PRE-DISPATCH: the fold run still grounds (manifest with
``member_graph_ids=[]``, seeded empty list), then the terminal ``RunStopped``
is minted ALONE — no CapacityInstance, because no capacity ran (guard G3, the
``record_cancelled`` argument verbatim).
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION,
    MANIFEST_MEMBER_GRAPH_IDS,
    MANIFEST_STOP_REASON_PHRASES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_RUN_MANIFEST,
    NODE_TYPE_RUN_STOPPED,
    PROP_CAPACITY_INSTANCE_TYPE,
    PROP_RUN_STOPPED_BEFORE,
    PROP_RUN_STOPPED_DETAIL,
    RUN_STOPPED_EMPTY_DOMAIN,
    capacity_iri,
    datastate_iri,
)
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

DS_COLL = datastate_iri("efd.exposures")
DS_MEMBER = datastate_iri("efd.exposure")
DS_SUB = datastate_iri("efd.verdict")
DS_OUT = datastate_iri("efd.verdicts")
DS_AGG = datastate_iri("efd.claim_conclusion")

CAP_SOLVE = capacity_iri(CATEGORY_DERIVATION, "efd_decide_one")
CAP_REDUCE = capacity_iri(CATEGORY_DERIVATION, "efd_conclude")

DESCRIPTIONS = {
    "efd.exposures": "the exposures the claim was split into",
    "efd.exposure": "one exposure, as filed",
    "efd.verdict": "what was decided about one exposure",
    "efd.verdicts": "each exposure's verdict, in order",
    "efd.claim_conclusion": "what the claim's verdicts add up to",
}
COLLECTIONS = {
    "efd.exposures": dict(collection=True, member_ds=DS_MEMBER),
    "efd.verdicts": dict(collection=True, member_ds=DS_SUB),
}

REDUCER_CALLS: list = []


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
    REDUCER_CALLS.append(kwargs.get(DS_OUT))
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
            name="efd_decide_one",
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
            name="efd_conclude",
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


def _plan() -> PlanResult:
    return PlanResult(
        plan_ref="plan:efd",
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


def _nodes(graph, type_name):
    return [n for n in graph.nodes.values() if n.type_name == type_name]


def _run(members):
    REDUCER_CALLS.clear()
    mm, dispatcher, writer, request_run = _harness()
    graphs: list = []
    execution.run(
        dispatcher, writer, _plan(), request_run,
        mm=mm, solve_seed={DS_COLL: list(members)},
        capacity_graphs=graphs,
    )
    return graphs, request_run


@pytest.fixture()
def empty_run():
    return _run([])


def test_an_empty_domain_never_dispatches_the_reducer(empty_run):
    """The reducer body is not called — a reducer 'concluding' from nothing
    would manufacture an epistemic claim out of machinery state."""
    assert REDUCER_CALLS == []


def test_the_stop_is_a_run_stopped_alone_with_the_empty_domain_reason(empty_run):
    """RunStopped minted ALONE — no CapacityInstance (G3: no capacity ran) —
    naming the reducer it stopped before, with a prose detail carrying no
    IRI (S-3: stopped_detail is prose-by-contract)."""
    graphs, _ = empty_run
    assert len(graphs) == 1
    fold = graphs[0]
    stopped = _nodes(fold, NODE_TYPE_RUN_STOPPED)
    assert len(stopped) == 1
    assert stopped[0].value == RUN_STOPPED_EMPTY_DOMAIN
    assert _nodes(fold, NODE_TYPE_CAPACITY_INSTANCE) == []
    props = stopped[0].properties or {}
    assert props.get(PROP_RUN_STOPPED_BEFORE) == CAP_REDUCE
    detail = props.get(PROP_RUN_STOPPED_DETAIL) or ""
    assert detail
    assert ":" not in detail, "an IRI-shaped fragment in a prose detail is a leak"


def test_the_stopped_fold_still_grounds_a_manifest_with_an_empty_member_list(empty_run):
    """The run grounds BEFORE it stops: manifest present, and
    member_graph_ids == [] — present-and-empty (a fold over zero members),
    which a reader must distinguish from the absent key of a non-fold run."""
    graphs, _ = empty_run
    manifests = _nodes(graphs[0], NODE_TYPE_RUN_MANIFEST)
    assert len(manifests) == 1
    assert manifests[0].value[MANIFEST_MEMBER_GRAPH_IDS] == []


def test_the_manifest_snapshot_translates_the_empty_domain_token(empty_run):
    """Tokens branch, phrases print: the stop's translation was already in
    the manifest snapshot when the run stopped — no renderer change."""
    graphs, _ = empty_run
    manifests = _nodes(graphs[0], NODE_TYPE_RUN_MANIFEST)
    phrases = manifests[0].value[MANIFEST_STOP_REASON_PHRASES]
    stopped = _nodes(graphs[0], NODE_TYPE_RUN_STOPPED)[0]
    assert phrases[stopped.value] == (
        "there was nothing to decide from - the collection had no members"
    )


def test_a_fold_only_plan_writes_no_member_ids_key_even_when_empty():
    """Critic s60 point 2: key presence means A MAP SUPPLIED IDS - never a
    fact about emptiness. A fold whose in_ds was seeded directly (no map)
    gets NO key whether its domain is empty or not; [] appears only when a
    map ran and yielded zero members. Without this pin, the stop path's old
    None->[] coercion made key presence flip on emptiness for a legal plan
    shape - a lying fold marker."""
    REDUCER_CALLS.clear()
    mm, dispatcher, writer, request_run = _harness()
    graphs: list = []
    fold_only = PlanResult(
        plan_ref="plan:efd-foldonly",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mFold"],
        pipeline_refs={"mFold": "pFold"},
        milestone_specs={
            "mFold": {"kind": "fold", "reducer_iri": CAP_REDUCE, "in_ds": DS_OUT},
        },
    )
    execution.run(
        dispatcher, writer, fold_only, request_run,
        mm=mm, solve_seed={DS_OUT: []},
        capacity_graphs=graphs,
    )
    assert REDUCER_CALLS == []
    assert len(graphs) == 1
    stopped = _nodes(graphs[0], NODE_TYPE_RUN_STOPPED)
    assert len(stopped) == 1
    assert stopped[0].value == RUN_STOPPED_EMPTY_DOMAIN
    manifests = _nodes(graphs[0], NODE_TYPE_RUN_MANIFEST)
    assert len(manifests) == 1
    assert MANIFEST_MEMBER_GRAPH_IDS not in manifests[0].value


def test_a_nonempty_domain_still_reaches_the_reducer():
    """The control: two members fold exactly as before this amendment."""
    graphs, _ = _run(["e0", "e1"])
    assert len(REDUCER_CALLS) == 1
    reducer_graphs = [
        g for g in graphs
        if any(
            n.properties.get(PROP_CAPACITY_INSTANCE_TYPE) == CAP_REDUCE
            for n in _nodes(g, NODE_TYPE_CAPACITY_INSTANCE)
        )
    ]
    assert len(reducer_graphs) == 1
    assert _nodes(reducer_graphs[0], NODE_TYPE_RUN_STOPPED) == []
