"""The run manifest — the three things a run's own nodes cannot say about it.

Probe D sketched a generic renderer over all four Decision Records run graphs
and recorded every symbol it could not turn into prose. There were exactly
three, and none of them is a value:

1. **Which values were given.** A parentless ``DataStateInstance`` is
   structurally identical to one whose producer was deleted. The mutation
   proof was a Record printing *"Given: a return must be filed"* — a derived
   conclusion silently reclassified as a premise. That is guard **G2**, and
   before this it was unimplementable: nothing in the graph would have let
   any renderer raise.
2. **What decided.** A ``CapacityInstance`` carries the capacity IRI and
   nothing else, and the criterion writes no origin record (ADR-0208 D3).
3. **Why a run stopped.** ``RunStopped.value`` is a token.

The manifest is also what makes **run 4** renderable: it is minted *before*
``_compose_pipeline``, so an unroutable request leaves a graph instead of only
an exception. That absorbs plan item 4a.
"""

from __future__ import annotations

import pytest

from mindsos_capacity.identifiers import (
    MANIFEST_CAPACITY_PHRASES,
    MANIFEST_CASE_LABEL,
    MANIFEST_DECLARED_STARTS,
    MANIFEST_STOP_REASON_PHRASES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    NODE_TYPE_RUN_MANIFEST,
    NODE_TYPE_RUN_STOPPED,
    PROP_DATASTATE_INSTANCE_TYPE,
    RUN_STOPPED_PHRASES,
    RUN_STOPPED_REASONS,
)
from mindsos_intelligence.execution import LeafPipelineNotFound

from ._dr_driver import decision_record_plan, run_decision_record
from ._dr_fixtures import (
    DS_AS_OF_DATE,
    CAP_DECISION,
    CAP_LOOKUP,
    CAP_READER,
    DS_FILING_RECORD,
    DS_FILING_VERDICT,
    INITIAL_2024,
    STARTS,
    build_kl_with_both,
)


def _manifests(graph):
    return [n for n in graph.nodes.values() if n.type_name == NODE_TYPE_RUN_MANIFEST]


def _the_manifest(graph):
    found = _manifests(graph)
    assert len(found) == 1, f"expected exactly one manifest, got {len(found)}"
    return found[0]


def _clean():
    return run_decision_record(build_kl_with_both(), INITIAL_2024, request_id="mf")


# ── shape ─────────────────────────────────────────────────────────────


def test_exactly_one_manifest_per_run():
    """Deterministic IRI, mirroring RunStopped — so 'one per run' is a
    structural fact, not a count that could drift."""
    assert len(_manifests(_clean().graph)) == 1


def test_the_manifest_carries_its_contents_in_the_value_not_the_properties():
    """``Graph.add_node`` validates properties as primitives only, and all
    three fields are collections. A dict value is also the shape probe C
    proved codec-safe with no encoders."""
    manifest = _the_manifest(_clean().graph)
    assert isinstance(manifest.value, dict)
    assert not (manifest.properties or {})
    assert set(manifest.value) == {
        MANIFEST_DECLARED_STARTS,
        MANIFEST_CAPACITY_PHRASES,
        MANIFEST_STOP_REASON_PHRASES,
        MANIFEST_CASE_LABEL,
    }


def test_the_manifest_is_not_a_datastate_instance_so_g7_is_unaffected():
    """A new node type, deliberately — the parentless-set guard counts
    DataStateInstances and must not notice this."""
    graph = _clean().graph
    parentless_types = {
        (n.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)
        for nid, n in graph.nodes.items()
        if n.type_name == NODE_TYPE_DATASTATE_INSTANCE
        and not [e for e in graph.edges.values() if e.target.node_id == nid]
    }
    assert parentless_types == set(STARTS)


# ── (1) which values were given ───────────────────────────────────────


def test_the_declared_starts_are_recorded():
    manifest = _the_manifest(_clean().graph)
    assert set(manifest.value[MANIFEST_DECLARED_STARTS]) == set(STARTS)


def test_each_declared_start_is_recorded_as_prose_not_as_an_iri():
    """It maps IRI → registered description, and the mapping is the point.

    Bare IRIs were the first version, and they printed straight onto the
    no-route page — where the starts are the only thing there is to say, so a
    G6 leak lands on the one page with nothing else to dilute it."""
    starts = _the_manifest(_clean().graph).value[MANIFEST_DECLARED_STARTS]
    assert starts == {
        DS_FILING_RECORD: "the return as filed",
        DS_AS_OF_DATE: "the date the question is asked about",
    }


def test_a_leaf_run_carries_the_callers_case_label():
    """Threaded from ``execution.run`` and never invented by core. Two runs of
    the same plan over different dates are otherwise indistinguishable on the
    page."""
    run = run_decision_record(
        build_kl_with_both(), INITIAL_2024, request_id="mf-label",
        case_label="the 2024 return",
    )
    manifest = _the_manifest(run.graph)
    assert manifest.value[MANIFEST_CASE_LABEL] == "the 2024 return"
    assert _the_manifest(_clean().graph).value[MANIFEST_CASE_LABEL] is None


def test_g2_a_deleted_producer_is_now_distinguishable_from_a_premise():
    """**G2.** Probe D's exact mutation: delete the criterion's
    CapacityInstance and the verdict's instance becomes parentless. Before the
    manifest a renderer printed it as *"Given: a return must be filed"*,
    because a parentless instance and a start were the same thing. With the
    manifest the two are separable — the verdict is parentless AND not a
    declared start, which is a gap.

    Remove ``writer.manifest(...)`` from ``execute_pipeline`` and this test
    goes red, because there is nothing left to compare against.
    """
    run = _clean()
    graph = run.graph
    declared = set(_the_manifest(graph).value[MANIFEST_DECLARED_STARTS])

    victim = next(
        nid for nid, n in graph.nodes.items()
        if n.type_name == NODE_TYPE_CAPACITY_INSTANCE and n.value == CAP_DECISION
    )
    graph.remove_node(victim)

    verdict = next(
        nid for nid, n in graph.nodes.items()
        if (n.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE) == DS_FILING_VERDICT
    )
    incoming = [e for e in graph.edges.values() if e.target.node_id == verdict]
    assert incoming == [], "the mutation must actually orphan the verdict"
    assert DS_FILING_VERDICT not in declared, (
        "parentless AND not declared: a renderer can now call this a gap "
        "rather than printing a derived conclusion as a premise"
    )
    assert DS_FILING_RECORD in declared, "a real premise stays a premise"


# ── (2) what decided ──────────────────────────────────────────────────


def test_every_composed_capacity_is_named_in_prose():
    phrases = _the_manifest(_clean().graph).value[MANIFEST_CAPACITY_PHRASES]
    assert phrases == {
        CAP_READER: "reading the return as filed",
        CAP_LOOKUP: "consulting the filing-threshold policy",
        CAP_DECISION: "the filing-requirement test",
    }


def test_the_phrase_is_snapshotted_not_looked_up_later():
    """ADR-0207 amendment 1: the catalog is mutable and separately persisted,
    so a Record must never reach back into it. Changing a declaration after
    the run must not change what the run recorded."""
    run = _clean()
    before = dict(_the_manifest(run.graph).value[MANIFEST_CAPACITY_PHRASES])
    second = run_decision_record(build_kl_with_both(), INITIAL_2024, request_id="mf2")
    assert _the_manifest(second.graph).value[MANIFEST_CAPACITY_PHRASES] == before


# ── (3) why a run stopped ─────────────────────────────────────────────


def test_the_manifest_refuses_a_none_member_graph_id():
    """am-6 finding, caught by a mutation pass: ``str(gid)`` coercion turned a
    None id into the truthy string "None" - a fake id that would persist and
    render, and that defeats any ``all(ids)`` guard downstream. A position
    with no grounding graph id is an upstream defect; the writer refuses it
    loudly instead of laundering it."""
    import pytest as _pytest

    from mindsos_intelligence.capacity_mm_writer import CapacityMMWriter
    from mindsos_intelligence.mm import MentalModel

    mm = MentalModel(session_id="s", user_id="u")
    w = CapacityMMWriter(mm, "mfr", "pipelinerun:mfr:0")
    with _pytest.raises(ValueError, match="non-empty strings"):
        w.manifest(
            declared_starts={}, capacity_phrases={},
            member_graph_ids=["gid-a", None, "gid-c"],
        )


def test_the_closed_stop_vocabulary_is_carried_in_full():
    """Every reason, not only the one that fired — whether the run will stop
    is not known when the manifest is minted, and a renderer must never
    translate a token itself."""
    phrases = _the_manifest(_clean().graph).value[MANIFEST_STOP_REASON_PHRASES]
    assert set(phrases) == set(RUN_STOPPED_REASONS)
    assert phrases == dict(RUN_STOPPED_PHRASES)


def test_an_outage_leaves_a_stop_whose_token_the_manifest_can_translate():
    run = run_decision_record(None, INITIAL_2024, request_id="mf-outage")
    graph = run.graph
    stopped = [n for n in graph.nodes.values() if n.type_name == NODE_TYPE_RUN_STOPPED]
    assert len(stopped) == 1
    phrases = _the_manifest(graph).value[MANIFEST_STOP_REASON_PHRASES]
    assert phrases[stopped[0].value] == "a step could not be completed"


# ── run 4 — the item this absorbs ─────────────────────────────────────


def test_run_4_leaves_a_graph_instead_of_only_an_exception():
    """Plan item 4a. ``_compose_pipeline`` still raises — the route really is
    unfindable and pretending otherwise would be worse — but the manifest is
    minted first, so there is now something to render."""
    graphs = []
    with pytest.raises(LeafPipelineNotFound):
        run_decision_record(
            build_kl_with_both(), INITIAL_2024, request_id="mf-noroute",
            plan=decision_record_plan(starts=(DS_FILING_RECORD,)),
            graphs=graphs,
        )
    assert len(graphs) == 1, "an unroutable run must still leave its graph"
    graph = graphs[0]
    manifest = _the_manifest(graph)
    assert manifest.value[MANIFEST_DECLARED_STARTS] == {
        DS_FILING_RECORD: "the return as filed"
    }
    assert manifest.value[MANIFEST_CAPACITY_PHRASES] == {}, (
        "no route means no capacity ran, so there is nothing to name — and a "
        "manifest that named one would be claiming an execution that did not "
        "happen, which is what G3 refuses"
    )
    assert [n for n in graph.nodes.values()
            if n.type_name == NODE_TYPE_CAPACITY_INSTANCE] == []


# ── one writer per run ────────────────────────────────────────────────


def test_minting_a_manifest_first_does_not_duplicate_any_instance():
    """The invariant a second writer would threaten, asserted directly.

    An earlier draft threaded the hoisted writer into ``execute_pipeline`` to
    prevent a double-mint. That justification was TESTED AND FALSIFIED — both
    writers resolve the same per-run graph by role, and the hoisted one mints
    only the manifest, which is neither indexed nor sequenced. The parameter
    was removed; this test is what would have caught the problem it claimed to
    solve, and it stands on its own as L-1: one instance per DataState IRI per
    run."""
    graph = _clean().graph
    per_type = {}
    for n in graph.nodes.values():
        if n.type_name != NODE_TYPE_DATASTATE_INSTANCE:
            continue
        t = (n.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)
        per_type[t] = per_type.get(t, 0) + 1
    assert all(c == 1 for c in per_type.values()), per_type
