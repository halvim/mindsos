"""Partial results (ADR-0201 amendment 6): a member stops IN PLACE and the
work that completed survives.

The shipped behaviour this replaces: one exposure's crash raised
``MemberAbortError``, skipped every sibling, dropped the failed member's own
grounding graph (only accepted attempts appended), and lost the claim's
Record entirely — while a member that asked for input was RE-ASKED to the
retry cap first. Owner rulings D1/D2/D5/D6 + critic §63 (coordination
§62–§65).

Harness is the fold-grounding family's, duplicated per house style.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION,
    MANIFEST_MEMBER_GRAPH_IDS,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_RUN_MANIFEST,
    NODE_TYPE_RUN_STOPPED,
    PROP_CAPACITY_INSTANCE_TYPE,
    RUN_STOPPED_EMPTY_DOMAIN,
    RUN_STOPPED_NEEDS_INPUT,
    RUN_STOPPED_PARTIAL_DOMAIN,
    RUN_STOPPED_STEP_FAILED,
    capacity_iri,
    datastate_iri,
)
from mindsos_capacity.needs_input import NeedsInput
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

DS_COLL = datastate_iri("prc.exposures")
DS_MEMBER = datastate_iri("prc.exposure")
DS_SUB = datastate_iri("prc.verdict")
DS_OUT = datastate_iri("prc.verdicts")
DS_AGG = datastate_iri("prc.claim_conclusion")

CAP_SOLVE = capacity_iri(CATEGORY_DERIVATION, "prc_decide_one")
CAP_REDUCE = capacity_iri(CATEGORY_DERIVATION, "prc_conclude")

DESCRIPTIONS = {
    "prc.exposures": "the exposures the claim was split into",
    "prc.exposure": "one exposure, as filed",
    "prc.verdict": "what was decided about one exposure",
    "prc.verdicts": "each exposure's verdict, in order",
    "prc.claim_conclusion": "what the claim's verdicts add up to",
}
COLLECTIONS = {
    "prc.exposures": dict(collection=True, member_ds=DS_MEMBER),
    "prc.verdicts": dict(collection=True, member_ds=DS_SUB),
}

MEMBER_CALLS: list = []
REDUCER_CALLS: list = []


class FakeSession:
    session_id = "s"
    user_id = "u"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability: str) -> bool:
        return False


def _ok_body(**kwargs):
    v = kwargs.get(DS_MEMBER)
    MEMBER_CALLS.append(v)
    return {DS_SUB: {"verdict": v}}


def _reduce_body(**kwargs):
    REDUCER_CALLS.append(kwargs.get(DS_OUT))
    return {DS_AGG: {"conclusion": kwargs.get(DS_OUT)}}


def _harness(member_impl=_ok_body):
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
            name="prc_decide_one",
            category=CATEGORY_DERIVATION,
            inputs=(DS_MEMBER,),
            outputs=(DS_SUB,),
            implementation=member_impl,
            description="one exposure -> its verdict",
        ),
        session=session,
    )
    layer.register_capacity(
        Capacity(
            name="prc_conclude",
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
        plan_ref="plan:prc",
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
    matches = [
        g for g in graphs
        if any(
            n.type_name == NODE_TYPE_RUN_STOPPED
            and n.value in (RUN_STOPPED_PARTIAL_DOMAIN, RUN_STOPPED_EMPTY_DOMAIN)
            for n in g.nodes.values()
        )
        or any(
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


def _run(members, *, member_impl=_ok_body, harness=None, blackboard=None,
         graphs=None, targeted=None, run_attempt=0):
    MEMBER_CALLS.clear()
    REDUCER_CALLS.clear()
    h = harness or _harness(member_impl)
    mm, dispatcher, writer, request_run = h
    graphs = graphs if graphs is not None else []
    execution.run(
        dispatcher, writer, _plan(), request_run,
        mm=mm, solve_seed={DS_COLL: list(members)},
        capacity_graphs=graphs, blackboard=blackboard,
        targeted=targeted, run_attempt=run_attempt,
    )
    return graphs, h


def _fail_m1(**kwargs):
    v = kwargs.get(DS_MEMBER)
    MEMBER_CALLS.append(v)
    if v == "e1":
        raise RuntimeError("exposure e1 machinery failure")
    return {DS_SUB: {"verdict": v}}


# ── the survival itself ───────────────────────────────────────────────


def test_siblings_survive_and_the_failed_members_stop_graph_is_retained():
    """The heart of the CR: the crash's own record persists (the final
    attempt's graph with its RunStopped) AND every sibling's work persists —
    losing four correct answers because the fifth crashed is over."""
    graphs, _ = _run(["e0", "e1", "e2"], member_impl=_fail_m1)
    assert "e2" in MEMBER_CALLS
    stop_graphs = [
        g for g in graphs
        if any(
            n.type_name == NODE_TYPE_RUN_STOPPED
            and n.value == RUN_STOPPED_STEP_FAILED
            for n in g.nodes.values()
        )
    ]
    assert len(stop_graphs) == 1, "the failed member's final attempt persists"
    completed_member_graphs = [
        g for g in graphs
        if any(
            n.properties.get(PROP_CAPACITY_INSTANCE_TYPE) == CAP_SOLVE
            for n in _nodes(g, NODE_TYPE_CAPACITY_INSTANCE)
        )
        and not _nodes(g, NODE_TYPE_RUN_STOPPED)
    ]
    assert len(completed_member_graphs) == 2


def test_the_fold_stops_partial_domain_with_the_full_id_list():
    """No conclusion from a machinery-truncated domain (D1); the manifest
    carries all N positions so the stopped member's page slot resolves."""
    graphs, _ = _run(["e0", "e1", "e2"], member_impl=_fail_m1)
    assert REDUCER_CALLS == []
    fold = _fold_graph(graphs)
    stopped = _nodes(fold, NODE_TYPE_RUN_STOPPED)
    assert len(stopped) == 1
    assert stopped[0].value == RUN_STOPPED_PARTIAL_DOMAIN
    assert _nodes(fold, NODE_TYPE_CAPACITY_INSTANCE) == []
    ids = _manifest_value(fold)[MANIFEST_MEMBER_GRAPH_IDS]
    assert len(ids) == 3
    assert all(gid for gid in ids), "every position resolves, stopped included"


def test_all_members_failing_is_partial_not_empty():
    """D1's boundary: empty_domain stays 'the map had ZERO members'. A domain
    truncated to nothing is still a TRUNCATED domain — the phrase 'the
    collection had no members' would lie."""

    def _fail_all(**kwargs):
        MEMBER_CALLS.append(kwargs.get(DS_MEMBER))
        raise RuntimeError("everything is down")

    graphs, _ = _run(["e0", "e1"], member_impl=_fail_all)
    fold = _fold_graph(graphs)
    assert _nodes(fold, NODE_TYPE_RUN_STOPPED)[0].value == RUN_STOPPED_PARTIAL_DOMAIN


def test_a_needs_input_member_is_asked_once_and_stops_in_place():
    """D6: no re-ask (inputs do not change between attempts — the am-6 rule),
    no abort. The member's graph carries RunStopped(needs_input); siblings
    run; the fold stops partial_domain."""

    def _ask_m1(**kwargs):
        v = kwargs.get(DS_MEMBER)
        MEMBER_CALLS.append(v)
        if v == "e1":
            return NeedsInput(
                question="which policy applies to this exposure?",
                missing=DS_SUB,
            )
        return {DS_SUB: {"verdict": v}}

    graphs, _ = _run(["e0", "e1", "e2"], member_impl=_ask_m1)
    assert MEMBER_CALLS.count("e1") == 1, "asked exactly once, never re-asked"
    assert "e2" in MEMBER_CALLS
    asks = [
        g for g in graphs
        if any(
            n.type_name == NODE_TYPE_RUN_STOPPED
            and n.value == RUN_STOPPED_NEEDS_INPUT
            for n in g.nodes.values()
        )
    ]
    assert len(asks) == 1
    assert _nodes(_fold_graph(graphs), NODE_TYPE_RUN_STOPPED)[0].value == (
        RUN_STOPPED_PARTIAL_DOMAIN
    )


def test_a_targeted_rerun_heals_the_partial_and_the_fold_concludes():
    """The recovery path D1 relies on: a Slice-3b targeted re-exec of the
    stopped member realigns outputs, ids and mask, and the re-run fold
    DISPATCHES — the conclusion exists and is ordered correctly."""
    flaky = {"broken": True}

    def _flaky_m1(**kwargs):
        v = kwargs.get(DS_MEMBER)
        MEMBER_CALLS.append(v)
        if v == "e1" and flaky["broken"]:
            raise RuntimeError("transient outage")
        return {DS_SUB: {"verdict": v}}

    harness = _harness(_flaky_m1)
    bb: dict = {DS_COLL: ["e0", "e1", "e2"]}
    graphs, harness = _run(
        ["e0", "e1", "e2"], harness=harness, blackboard=bb,
    )
    assert REDUCER_CALLS == []
    flaky["broken"] = False
    graphs, _ = _run(
        ["e0", "e1", "e2"], harness=harness, blackboard=bb, graphs=graphs,
        targeted=(0, 1), run_attempt=1,
    )
    assert len(REDUCER_CALLS) == 1
    assert REDUCER_CALLS[0] == [
        {"verdict": "e0"}, {"verdict": "e1"}, {"verdict": "e2"}
    ]
    new_fold = _fold_graph(graphs[-2:] if len(graphs) >= 2 else graphs)
    ids = _manifest_value(new_fold)[MANIFEST_MEMBER_GRAPH_IDS]
    assert len(ids) == 3 and all(ids)


# ── the record and its classifier ─────────────────────────────────────


def test_the_terminal_attempt_classifier_reads_stopped_short():
    graphs, h = _run(["e0", "e1", "e2"], member_impl=_fail_m1)
    mm, dispatcher, writer, request_run = h
    assert execution.terminal_attempt_stopped_short(
        writer.chain_graph(), request_run
    ) is True


def test_a_clean_run_is_not_stopped_short():
    graphs, h = _run(["e0", "e1"])
    mm, dispatcher, writer, request_run = h
    assert execution.terminal_attempt_stopped_short(
        writer.chain_graph(), request_run
    ) is False


def test_the_classifier_raises_on_an_unknown_status_never_defaults():
    """§63 Q3: the vocabulary is CLOSED. A word outside it is a defect to
    surface, not a case to shrug past."""
    graphs, h = _run(["e0", "e1"])
    mm, dispatcher, writer, request_run = h
    chain = writer.chain_graph()
    chain.nodes[request_run.pipeline_runs[0]].value.status = "wombat"
    with pytest.raises(ValueError, match="closed"):
        execution.terminal_attempt_stopped_short(chain, request_run)


def test_the_fold_raises_when_values_and_mask_disagree():
    """am-6 coherence: the record and the value bus in step, or loud."""
    mm, dispatcher, writer, request_run = _harness()
    graphs: list = []
    bb: dict = {DS_COLL: ["e0", "e1"]}
    execution.run(
        dispatcher, writer, _plan(), request_run,
        mm=mm, solve_seed={DS_COLL: ["e0", "e1"]},
        capacity_graphs=graphs, blackboard=bb,
    )
    bb[execution.member_completed_key(DS_OUT)] = [True, False]
    writer2_run = writer.emit_request_run()
    with pytest.raises(ValueError, match="out of step"):
        execution.run(
            dispatcher, writer, _plan(), writer2_run,
            mm=mm, solve_seed={DS_COLL: ["e0", "e1"]},
            capacity_graphs=graphs, blackboard=bb,
            targeted=(1, None),
            run_attempt=1,
        )
