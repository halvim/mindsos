"""The fold grounds — including the claim-level conclusion, which grounded nowhere.

``_run_fold_milestone`` used to dispatch the reducer **directly**, and its
signature did not even take ``mm``, so it had no way to ground anything: no
``RunManifest``, no reducer ``CapacityInstance``, no conclusion
``DataStateInstance``, no CONSUMES edge from the member verdicts to the
conclusion. Proven by **running** a map + fold through ``execution.run`` with
``mm=`` and dumping every graph in ``capacity_mm`` — members present, reducer
absent, conclusion absent — and independently reproduced by the critic lane
(3-member: manifests=3, reducer_CapacityInstance=0,
claim_conclusion_DataStateInstance=0). The demo's headline shape is one Record
per exposure PLUS a claim-level conclusion, and the conclusion is the thing a
reader cares about most; it lived only on the in-memory blackboard, which
``execution.run`` never hands back. Unrenderable.

The fix is the one PR #157 set the precedent for: route the reducer through
``execute_pipeline`` — the ONE function that grounds — rather than adding a
third hand-mint; a hand-mint is how ``_run_member_pipeline`` came to differ
from ``_run_leaf_pipeline`` in the first place. Everything asserted here then
comes from the executor, unduplicated: manifest first, seeded starts, the
invocation, the produced conclusion, ``RunStopped`` on a non-success.

Which member produced which verdict stays **structural**, not a manifest field:
the ref-path is the provenance tree (Slice 2) — member runs ground under
``…:0:m{i}:…``, the fold under its own milestone index, same request id — and
the fold's seeded collection preserves the members' order. One test here pins
that correlation by value.

Registrations carry real prose descriptions and ``printable_phrase``\\ s, as in
``test_map_member_manifest``: the thing under test is whether a page can be
rendered from the fold's graph alone, and a fixture whose phrase is its own IRI
cannot tell a leak from a translation.
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION,
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    MANIFEST_CAPACITY_PHRASES,
    MANIFEST_CASE_LABEL,
    MANIFEST_DECLARED_STARTS,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    NODE_TYPE_RUN_MANIFEST,
    NODE_TYPE_RUN_STOPPED,
    PROP_CAPACITY_INSTANCE_TYPE,
    PROP_DATASTATE_INSTANCE_TYPE,
    RUN_STOPPED_STEP_FAILED,
    capacity_iri,
    datastate_iri,
)
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

DS_COLL = datastate_iri("fgx.exposures")
DS_MEMBER = datastate_iri("fgx.exposure")
DS_SUB = datastate_iri("fgx.verdict")
DS_OUT = datastate_iri("fgx.verdicts")
DS_AGG = datastate_iri("fgx.claim_conclusion")

CAP_SOLVE = capacity_iri(CATEGORY_DERIVATION, "fgx_decide_one")
CAP_REDUCE = capacity_iri(CATEGORY_DERIVATION, "fgx_conclude")

REDUCE_PHRASE = "concluding the claim from its exposure verdicts"
OUT_PROSE = "each exposure's verdict, in order"

DESCRIPTIONS = {
    "fgx.exposures": "the exposures the claim was split into",
    "fgx.exposure": "one exposure, as filed",
    "fgx.verdict": "what was decided about one exposure",
    "fgx.verdicts": OUT_PROSE,
    "fgx.claim_conclusion": "what the claim's verdicts add up to",
}
COLLECTIONS = {
    "fgx.exposures": dict(collection=True, member_ds=DS_MEMBER),
    "fgx.verdicts": dict(collection=True, member_ds=DS_SUB),
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


def _failing_reduce_body(**kwargs):
    raise RuntimeError("the reducer could not conclude")


def _harness(reduce_impl=_reduce_body):
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
            name="fgx_decide_one",
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
            name="fgx_conclude",
            category=CATEGORY_DERIVATION,
            inputs=(DS_OUT,),
            outputs=(DS_AGG,),
            implementation=reduce_impl,
            description="the ordered verdicts -> the claim conclusion",
            printable_phrase=REDUCE_PHRASE,
        ),
        session=session,
    )
    mm = MentalModel(session_id="s", user_id="u")
    dispatcher = L4Dispatcher(layer, session=session)
    writer = ChainArtifactWriter(mm, "t")
    return mm, dispatcher, writer, writer.emit_request_run()


def _plan() -> PlanResult:
    return PlanResult(
        plan_ref="plan:fgx",
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


def _fold_graph(graphs):
    """The one graph holding the reducer's CapacityInstance — this selector
    finding nothing IS the shipped defect."""
    matches = [
        g for g in graphs
        if any(
            n.properties.get(PROP_CAPACITY_INSTANCE_TYPE) == CAP_REDUCE
            for n in _nodes(g, NODE_TYPE_CAPACITY_INSTANCE)
        )
    ]
    assert len(matches) == 1, (
        f"expected exactly one fold graph naming the reducer, got "
        f"{len(matches)} of {len(graphs)} graphs"
    )
    return matches[0]


def _run(members, *, reduce_impl=_reduce_body, case_label=None):
    mm, dispatcher, writer, request_run = _harness(reduce_impl)
    graphs: list = []
    execution.run(
        dispatcher, writer, _plan(), request_run,
        mm=mm, solve_seed={DS_COLL: list(members)},
        capacity_graphs=graphs, case_label=case_label,
    )
    return graphs, request_run


# ── the gap itself ────────────────────────────────────────────────────


def test_the_fold_leaves_its_own_grounding_graph():
    """**The finding, as a count.** Three members used to leave 3 graphs and
    the fold left nothing; now the fold's graph is the fourth, and it is the
    only one naming the reducer."""
    graphs, _ = _run(["e1", "e2", "e3"])
    assert len(graphs) == 4
    _fold_graph(graphs)


def test_the_fold_graph_carries_exactly_one_manifest():
    """Manifest-first is the executor's property now, so the fold inherits it:
    the ordered-verdicts start named in prose, the reducer's phrase
    snapshotted."""
    graphs, _ = _run(["e1", "e2"])
    fold = _fold_graph(graphs)
    manifests = _nodes(fold, NODE_TYPE_RUN_MANIFEST)
    assert len(manifests) == 1
    manifest = manifests[0]
    assert manifest.value[MANIFEST_DECLARED_STARTS] == {DS_OUT: OUT_PROSE}
    assert manifest.value[MANIFEST_CAPACITY_PHRASES] == {CAP_REDUCE: REDUCE_PHRASE}


def test_the_claim_conclusion_is_produced_not_given():
    """The conclusion is a ``DataStateInstance`` the reducer PRODUCES. The one
    parentless instance is the seeded ordered-verdicts collection — so G2's
    precondition holds on the fold graph: a premise the run was given and a
    derived conclusion are structurally distinct."""
    graphs, _ = _run(["e1", "e2"])
    fold = _fold_graph(graphs)
    by_ds = {
        n.properties[PROP_DATASTATE_INSTANCE_TYPE]: n
        for n in _nodes(fold, NODE_TYPE_DATASTATE_INSTANCE)
    }
    assert set(by_ds) == {DS_OUT, DS_AGG}
    produced = {
        e.target.properties[PROP_DATASTATE_INSTANCE_TYPE]
        for e in fold.edges.values()
        if e.type_name == EDGE_PRODUCES
    }
    assert produced == {DS_AGG}
    assert by_ds[DS_AGG].value == {
        "conclusion": [{"verdict": "e1"}, {"verdict": "e2"}]
    }


def test_the_reducer_consumes_the_ordered_member_verdicts():
    """One CONSUMES edge, from the collection whose value IS the ordered member
    verdicts. Which member produced which verdict is order-correlated with the
    member graphs — pinned here by value: the fold's seeded collection equals
    the member graphs' verdict instances, in member order."""
    graphs, _ = _run(["e1", "e2", "e3"])
    fold = _fold_graph(graphs)
    consumed = [
        (e.source, e.target)
        for e in fold.edges.values()
        if e.type_name == EDGE_CONSUMES
    ]
    assert len(consumed) == 1
    source, target = consumed[0]
    assert source.properties[PROP_DATASTATE_INSTANCE_TYPE] == DS_OUT
    assert target.properties[PROP_CAPACITY_INSTANCE_TYPE] == CAP_REDUCE
    member_graphs = [g for g in graphs if g is not fold]
    member_verdicts = []
    for g in member_graphs:
        verdicts = [
            n.value
            for n in _nodes(g, NODE_TYPE_DATASTATE_INSTANCE)
            if n.properties[PROP_DATASTATE_INSTANCE_TYPE] == DS_SUB
        ]
        assert len(verdicts) == 1
        member_verdicts.append(verdicts[0])
    assert source.value == member_verdicts == [
        {"verdict": "e1"}, {"verdict": "e2"}, {"verdict": "e3"}
    ]


def test_the_fold_runs_under_its_own_fresh_run_ref():
    """Four graphs, four distinct roles — the fold's ref is its own milestone
    position, never a member's (Slice-A isolation extends to the fold)."""
    graphs, _ = _run(["e1", "e2", "e3"])
    roles = [g.role for g in graphs]
    assert len(set(roles)) == 4, roles


def test_the_case_label_reaches_the_fold_manifest_verbatim():
    """The claim-level page is the one a label matters most on — several
    Records from one claim are otherwise indistinguishable."""
    graphs, _ = _run(["e1"], case_label="the March claim")
    fold = _fold_graph(graphs)
    manifest = _nodes(fold, NODE_TYPE_RUN_MANIFEST)[0]
    assert manifest.value[MANIFEST_CASE_LABEL] == "the March claim"


def test_a_replan_reattempt_folds_into_a_fresh_graph():
    """Slice-A isolation extends to the fold: the fold's run ref carries
    ``run_attempt``, so a replan re-run grounds a second fold graph instead of
    overwriting the first. Every graph of both attempts keeps a distinct
    role."""
    mm, dispatcher, writer, request_run = _harness()
    graphs: list = []
    for attempt in (0, 1):
        execution.run(
            dispatcher, writer, _plan(), request_run,
            mm=mm, solve_seed={DS_COLL: ["e1", "e2"]},
            capacity_graphs=graphs, run_attempt=attempt,
        )
    assert len(graphs) == 6  # (2 members + 1 fold) x 2 attempts
    roles = [g.role for g in graphs]
    assert len(set(roles)) == 6, roles
    fold_graphs = [
        g for g in graphs
        if any(
            n.properties.get(PROP_CAPACITY_INSTANCE_TYPE) == CAP_REDUCE
            for n in _nodes(g, NODE_TYPE_CAPACITY_INSTANCE)
        )
    ]
    assert len(fold_graphs) == 2
    assert fold_graphs[0].role != fold_graphs[1].role


def test_the_fold_pipeline_object_declares_the_reducers_true_shape():
    """``_fold_pipeline`` builds the single-step Pipeline the executor grounds.
    The graph itself never reads the step's ``output_datastates`` or the
    ``target_datastate`` — a mutation blanking them reddened nothing, which is
    exactly how dead-but-wrong data survives until a consumer (the dump, the
    renderer) trusts it. So the object's claims are pinned here: the step
    declares the reducer's REGISTERED outputs, resolved scope-correctly, and
    the target is the reducer's conclusion — never the fold's own input."""
    _, dispatcher, _, _ = _harness()
    pipeline = execution._fold_pipeline(dispatcher, CAP_REDUCE, DS_OUT)
    assert pipeline.start_datastates == (DS_OUT,)
    assert pipeline.target_datastate == DS_AGG
    assert len(pipeline.steps) == 1
    step = pipeline.steps[0]
    assert step.capacity_iri == CAP_REDUCE
    assert step.input_datastates == (DS_OUT,)
    assert step.output_datastates == (DS_AGG,)


# ── a failed reducer, which used to leave nothing at all ──────────────


def test_a_failed_reducer_leaves_a_terminal_node_not_nothing():
    """The invocation happened, so it is in the graph: CapacityInstance +
    CONSUMES, then ``RunStopped`` naming ``step_failed`` — and no conclusion
    instance, because none was produced. L4-side semantics are unchanged: the
    fold's PipelineRun fails, nothing aborts, the run returns."""
    graphs, request_run = _run(["e1", "e2"], reduce_impl=_failing_reduce_body)
    assert len(graphs) == 3
    fold = _fold_graph(graphs)
    stops = _nodes(fold, NODE_TYPE_RUN_STOPPED)
    assert len(stops) == 1
    assert stops[0].value == RUN_STOPPED_STEP_FAILED
    assert [
        n.properties[PROP_DATASTATE_INSTANCE_TYPE]
        for n in _nodes(fold, NODE_TYPE_DATASTATE_INSTANCE)
    ] == [DS_OUT]
    assert len(request_run.pipeline_runs) == 2
