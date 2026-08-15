"""Every run leaves a manifest — including a map member's, which had none.

The run manifest shipped minting inside ``execution._run_leaf_pipeline``. That
is one of **two** run paths: a map member goes through
``_run_member_pipeline`` instead, and nothing on that path minted anything. So
the ship note's "every run leaves a graph" was false for every map member, and
it was false the day it was written.

It was found by **running** a three-member map and counting what came out —
3 graphs, 3 CapacityInstances each, 0 manifests — not by reading the code. The
fix is not another mint: minting moved into ``execute_pipeline``, the one
function both paths call, so "every graph carries a manifest" is a property of
the executor instead of a thing each caller has to remember.

Two facts are pinned here, both by driving the executor:

* a map member's grounding graph carries exactly one manifest, naming its
  member start in prose and snapshotting the member capacity's phrase;
* a member with **no route** leaves a manifest-only graph instead of nothing at
  all. Before this, ``_compose_pipeline`` raised straight out through
  ``_run_member_pipeline``, so the member left no graph and the abort that
  followed took the whole request's Record with it — the reader got an
  exception where a page should have been.

Registrations here carry **real prose** descriptions and ``printable_phrase``\\ s,
unlike ``test_slice1b_map_fold``'s ``description=name``. That is deliberate: the
thing under test is whether the manifest can be *read by a person*, and a
fixture whose phrase is its own IRI cannot tell a leak from a translation.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION,
    MANIFEST_CAPACITY_PHRASES,
    MANIFEST_CASE_LABEL,
    MANIFEST_DECLARED_STARTS,
    MANIFEST_STOP_REASON_PHRASES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_RUN_MANIFEST,
    RUN_STOPPED_PHRASES,
    capacity_iri,
    datastate_iri,
)
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

DS_COLL = datastate_iri("mfx.readings")
DS_MEMBER = datastate_iri("mfx.reading")
DS_SUB = datastate_iri("mfx.reading_fact")
DS_OUT = datastate_iri("mfx.reading_facts")
DS_UNREACHED = datastate_iri("mfx.nothing_produces_this")

CAP_SOLVE = capacity_iri(CATEGORY_DERIVATION, "mfx_solve")

MEMBER_PHRASE = "reading the meter as recorded"
MEMBER_START_PROSE = "one meter reading, as recorded"

DESCRIPTIONS = {
    "mfx.readings": "the meter readings the request was given",
    "mfx.reading": MEMBER_START_PROSE,
    "mfx.reading_fact": "what was concluded about one reading",
    "mfx.reading_facts": "what was concluded about each reading, in order",
    "mfx.nothing_produces_this": "something nothing here can work out",
}
COLLECTIONS = {
    "mfx.readings": dict(collection=True, member_ds=DS_MEMBER),
    "mfx.reading_facts": dict(collection=True, member_ds=DS_SUB),
}


class FakeSession:
    session_id = "s"
    user_id = "u"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability: str) -> bool:
        return False


def _member_body(**kwargs):
    return {DS_SUB: {"solved": kwargs.get(DS_MEMBER)}}


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
            name="mfx_solve",
            category=CATEGORY_DERIVATION,
            inputs=(DS_MEMBER,),
            outputs=(DS_SUB,),
            implementation=_member_body,
            description="member: reading -> fact",
            printable_phrase=MEMBER_PHRASE,
        ),
        session=session,
    )
    mm = MentalModel(session_id="s", user_id="u")
    dispatcher = L4Dispatcher(layer, session=session)
    writer = ChainArtifactWriter(mm, "t")
    return mm, dispatcher, writer, writer.emit_request_run()


def _map_plan(sub_target: str = DS_SUB) -> PlanResult:
    return PlanResult(
        plan_ref="plan:mfx",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mMap"],
        pipeline_refs={"mMap": "pMap"},
        milestone_specs={
            "mMap": {
                "kind": "map", "collection_ds": DS_COLL, "member_ds": DS_MEMBER,
                "sub_target": sub_target, "out_ds": DS_OUT,
            },
        },
    )


def _manifests(graph):
    return [n for n in graph.nodes.values() if n.type_name == NODE_TYPE_RUN_MANIFEST]


def _run_map(members, *, sub_target=DS_SUB, case_label=None):
    """Drive one map and return its per-member grounding graphs."""
    mm, dispatcher, writer, request_run = _harness()
    graphs: list = []
    execution.run(
        dispatcher, writer, _map_plan(sub_target), request_run,
        mm=mm, solve_seed={DS_COLL: list(members)},
        capacity_graphs=graphs, case_label=case_label,
    )
    return graphs


# ── the gap itself ────────────────────────────────────────────────────


def test_every_map_member_graph_carries_exactly_one_manifest():
    """**The finding, as a count.** This was ``0`` for every member.

    Three members so the assertion is about *every* graph rather than about
    the one a single-member run happens to produce."""
    graphs = _run_map(["r1", "r2", "r3"])
    assert len(graphs) == 3
    assert [len(_manifests(g)) for g in graphs] == [1, 1, 1]


def test_a_member_manifest_names_its_start_in_prose_not_as_an_iri():
    """``declared_starts`` maps IRI → registered description. The member value
    is the one premise a member run is given, and on a member's page it is the
    only thing there is to say about where anything came from."""
    manifest = _manifests(_run_map(["r1"])[0])[0]
    assert manifest.value[MANIFEST_DECLARED_STARTS] == {
        DS_MEMBER: MEMBER_START_PROSE
    }


def test_a_member_manifest_snapshots_the_member_capacitys_phrase():
    manifest = _manifests(_run_map(["r1"])[0])[0]
    assert manifest.value[MANIFEST_CAPACITY_PHRASES] == {CAP_SOLVE: MEMBER_PHRASE}


def test_a_member_manifest_carries_the_closed_stop_vocabulary_in_full():
    """Whether a member will stop is not known when its manifest is minted, so
    the whole set travels — a renderer must never translate a token itself."""
    manifest = _manifests(_run_map(["r1"])[0])[0]
    assert manifest.value[MANIFEST_STOP_REASON_PHRASES] == dict(RUN_STOPPED_PHRASES)


def test_each_member_manifest_belongs_to_its_own_isolated_graph():
    """One manifest per member, in the member's own graph — not one manifest
    for the map. A map member is a run; the manifest is per run."""
    graphs = _run_map(["r1", "r2", "r3"])
    roles = [g.role for g in graphs]
    assert len(set(roles)) == 3, roles


# ── the case label ────────────────────────────────────────────────────


def test_the_case_label_reaches_every_member_verbatim():
    """Several Records from one claim are otherwise indistinguishable on the
    page. The label is the caller's, carried unchanged."""
    graphs = _run_map(["r1", "r2"], case_label="the March claim")
    for graph in graphs:
        assert _manifests(graph)[0].value[MANIFEST_CASE_LABEL] == "the March claim"


def test_no_case_label_records_absence_rather_than_an_invented_one():
    """Core must never invent one. ``None`` is recorded, and recorded is the
    point: a renderer can tell "this run carried no label" from "I could not
    read the label", which a missing key would not allow."""
    manifest = _manifests(_run_map(["r1"])[0])[0]
    assert MANIFEST_CASE_LABEL in manifest.value
    assert manifest.value[MANIFEST_CASE_LABEL] is None


# ── the second half of the gap: a member with no route ────────────────


def test_a_member_with_no_route_still_leaves_a_graph():
    """**The half that destroyed the whole Record — now fully closed.**
    RESTATED by ADR-0201 am-6: the no-route member used to leave its
    manifest-only graph and then RAISE ``LeafPipelineNotFound``, aborting the
    request anyway. Under partial results the member stops IN PLACE — no
    raise, the run completes — and every graph assertion below is the KEPT
    half, verbatim: the manifest-only graph with its prose starts and case
    label is exactly what renders as the no-route stop (the run-4
    precedent)."""
    mm, dispatcher, writer, request_run = _harness()
    graphs: list = []
    execution.run(
        dispatcher, writer, _map_plan(DS_UNREACHED), request_run,
        mm=mm, solve_seed={DS_COLL: ["r1"]},
        capacity_graphs=graphs, case_label="unroutable",
    )
    assert len(graphs) == 1, "an unroutable member must still leave its graph"
    manifest = _manifests(graphs[0])[0]
    assert manifest.value[MANIFEST_DECLARED_STARTS] == {DS_MEMBER: MEMBER_START_PROSE}
    assert manifest.value[MANIFEST_CASE_LABEL] == "unroutable"


def test_a_no_route_member_names_no_capacity_because_none_ran():
    """A manifest that named one would be claiming an execution that did not
    happen. (RESTATED by am-6: no raise — the member stops in place; the
    manifest-only shape is the kept half, verbatim.)"""
    mm, dispatcher, writer, request_run = _harness()
    graphs: list = []
    execution.run(
        dispatcher, writer, _map_plan(DS_UNREACHED), request_run,
        mm=mm, solve_seed={DS_COLL: ["r1"]}, capacity_graphs=graphs,
    )
    graph = graphs[0]
    assert _manifests(graph)[0].value[MANIFEST_CAPACITY_PHRASES] == {}
    assert [n for n in graph.nodes.values()
            if n.type_name == NODE_TYPE_CAPACITY_INSTANCE] == []
    assert len(graph.nodes) == 1, (
        "manifest-only: nothing ran, so nothing else may be in there"
    )


def test_the_no_route_helper_writes_nothing_when_there_is_no_mm():
    """The value-only path has no graph to leave, and must not acquire one.
    Driven rather than asserted over a set: ``mm=None`` is the sanctioned
    no-grounding path (interpret-resolve, isolated tests)."""
    _, dispatcher, _, _ = _harness()
    graphs: list = []
    execution._mint_no_route_graph(
        dispatcher, None, "t", "pipelinerun:t:0:0", (DS_MEMBER,), graphs, None,
    )
    assert graphs == []
