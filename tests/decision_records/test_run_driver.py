"""Item 4 — the route is FOUND by L4 and GROUNDED, not assembled here.

Item 3's route test calls ``ConjunctionFinder`` directly. That was right for
pinning composition and is exactly what a driver must not do: selecting a finder
is L4's (``execution._select_finder``; ``find_pipeline``'s own docstring says
*"selected by L4"*), and a subsystem that hard-selects one owns a core mechanism
under RULES §8. Here the driver states two endpoints and nothing else — L4
derives the finder from start **arity**, composes, and grounds.

The difference is the whole acceptance. A slice that hand-wires its pipeline and
then reports numbers off it reproduces the arc1 failure
``BRAIN_ARCHITECTURE_AUDIT.md`` records: a registered topology the solver never
executed through.
"""

from __future__ import annotations

import pytest

from mindsos_capacity.builtins.origin_v0 import (
    FIELD_ADMITTED,
    FIELD_REFUSAL_REASON,
    FIELD_SOURCE_VERSION,
    REFUSAL_FIELD_ABSENT,
    REFUSAL_NO_SOURCE_IN_FORCE,
)
from mindsos_capacity.identifiers import (
    EDGE_CONSUMES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    NODE_TYPE_RUN_STOPPED,
    PROP_CAPACITY_INSTANCE_TYPE,
    PROP_DATASTATE_INSTANCE_TYPE,
    PROP_RUN_STOPPED_DETAIL,
    RUN_STOPPED_STEP_FAILED,
)

from . import _dr_driver
from ._dr_driver import decision_record_plan, run_decision_record
from ._dr_fixtures import (
    CAP_DECISION,
    CAP_LOOKUP,
    CAP_READER,
    DS_AS_OF_DATE,
    DS_FILING_RECORD,
    DS_FILING_THRESHOLD,
    DS_FILING_THRESHOLD_ORIGIN,
    DS_FILING_VERDICT,
    DS_GROSS_INCOME,
    DS_GROSS_INCOME_ORIGIN,
    EDITION_2023,
    INITIAL_2023,
    INITIAL_2024,
    INITIAL_NO_INCOME,
    INITIAL_UNCOVERED,
    POLICY_PHRASE,
    STARTS,
    VERDICT_MUST_FILE,
    VERDICT_NOT_DETERMINED,
    build_kl,
    build_kl_with_both,
)


def _instances(graph, type_name, prop, value):
    return [
        n for n in graph.nodes.values()
        if n.type_name == type_name and (n.properties or {}).get(prop) == value
    ]


# ── the ownership boundary ────────────────────────────────────────────


def test_the_driver_names_no_finder():
    """Structural, because a comment saying "L4 picks the finder" is not a
    guard. If a later edit reaches for ``ConjunctionFinder`` to make something
    pass, this goes red at the source rather than after the fact.

    Walks the AST rather than grepping the text: the module's own docstring
    explains at length *why* it does not select a finder, and a text search
    cannot tell an explanation from a call. Checked here are the things that
    would actually do it — imported names, referenced identifiers, attribute
    names, and the ``finder`` plan key.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(_dr_driver))
    referenced = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            referenced.add(node.id)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
        elif isinstance(node, ast.alias):
            referenced.add(node.name.split(".")[-1])
            if node.asname:
                referenced.add(node.asname)
        elif isinstance(node, ast.ImportFrom) and node.module:
            referenced.add(node.module.split(".")[-1])
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # A plan key is a string literal, so string CONSTANTS are checked —
            # but a docstring is a Constant too, so match exactly, not by
            # substring.
            if node.value == "finder":
                referenced.add("finder-key")
    for banned in ("ConjunctionFinder", "BFSFinder", "find_pipeline", "pipeline",
                   "finder-key"):
        assert banned not in referenced, (
            f"the run driver references {banned!r}; selecting a finder is L4's "
            f"(RULES §8, ADR-0205) and the plan states endpoints only"
        )


def test_the_plan_declares_plural_starts_and_no_finder_override():
    leaf = decision_record_plan().leaf_targets["mDecisionRecord"]
    assert leaf["start_datastates"] == list(STARTS)
    assert "start_datastate" not in leaf
    assert "finder" not in leaf


# ── the clean run ─────────────────────────────────────────────────────


def test_the_driven_route_reaches_the_verdict():
    run = run_decision_record(build_kl_with_both(), INITIAL_2024)
    assert run.graph is not None, "no grounding graph — the run fell back to the notional record"
    assert run.value_of(DS_FILING_VERDICT) == VERDICT_MUST_FILE
    assert run.value_of(DS_FILING_THRESHOLD) == 29200


def test_l4_composed_all_three_capacities():
    run = run_decision_record(build_kl_with_both(), INITIAL_2024)
    composed = {
        (n.properties or {}).get(PROP_CAPACITY_INSTANCE_TYPE)
        for n in run.graph.nodes.values()
        if n.type_name == NODE_TYPE_CAPACITY_INSTANCE
    }
    assert composed == {CAP_READER, CAP_LOOKUP, CAP_DECISION}


def test_the_derivation_is_in_the_graph():
    run = run_decision_record(build_kl_with_both(), INITIAL_2024)
    graph = run.graph
    decisions = _instances(
        graph, NODE_TYPE_CAPACITY_INSTANCE, PROP_CAPACITY_INSTANCE_TYPE, CAP_DECISION
    )
    assert len(decisions) == 1
    consumed = {
        (e.source.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)
        for e in graph.edges.values()
        if e.type_name == EDGE_CONSUMES and e.target.node_id == decisions[0].node_id
    }
    assert consumed == {DS_GROSS_INCOME, DS_FILING_THRESHOLD}


def test_g7_holds_on_the_l4_driven_graph():
    """G7 again, and not redundantly. Item 3 asserts it over a pipeline this
    lane composed; here L4 composed it and ``_run_leaf_pipeline`` chose what to
    seed — a different seeding path, and the one the product actually runs."""
    run = run_decision_record(build_kl_with_both(), INITIAL_2024)
    graph = run.graph
    has_incoming = {e.target.node_id for e in graph.edges.values()}
    parentless = {
        (n.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)
        for n in graph.nodes.values()
        if n.type_name == NODE_TYPE_DATASTATE_INSTANCE
        and n.node_id not in has_incoming
    }
    assert parentless == set(STARTS)


def test_no_grounding_root_was_pre_minted():
    """The plan's item-4 line, corrected and pinned rather than just dropped.

    Pre-minting the document as a root through ``execution.run`` mints it twice
    — ``execute_pipeline`` builds its own ``CapacityMMWriter`` with an empty
    ``index`` and re-seeds. Both copies are parentless, so G7 above would still
    pass on a set comparison while the graph carried an orphan. This asserts the
    count, which is what G7 cannot see.
    """
    run = run_decision_record(build_kl_with_both(), INITIAL_2024)
    for start in STARTS:
        assert len(
            _instances(
                run.graph, NODE_TYPE_DATASTATE_INSTANCE,
                PROP_DATASTATE_INSTANCE_TYPE, start,
            )
        ) == 1, f"{start} has more than one instance — a pre-minted root duplicates a seeded start"


def test_g5_two_dates_over_one_store_give_two_records():
    """Run 5, driven. The as-of date is a start DataState, never read out of the
    document, or this silently becomes "two documents disagree"."""
    kl = build_kl_with_both()
    old = run_decision_record(kl, INITIAL_2023, request_id="dr-2023")
    new = run_decision_record(kl, INITIAL_2024, request_id="dr-2024")
    assert (old.value_of(DS_FILING_THRESHOLD), new.value_of(DS_FILING_THRESHOLD)) == (
        27700, 29200,
    )
    assert old.value_of(DS_FILING_THRESHOLD_ORIGIN)[FIELD_SOURCE_VERSION] == "2023.1"
    assert new.value_of(DS_FILING_THRESHOLD_ORIGIN)[FIELD_SOURCE_VERSION] == "2024.1"


# ── the two refusals, driven ──────────────────────────────────────────


def test_run_2_a_return_that_states_no_income_still_produces_a_record():
    """**RUN 2, and until this test it had never been executed.** v0 is
    defined as runs 1 and 2; every seed in this module carried an income, so
    the reader's refusal branch was unreachable from any committed test. The
    plan claimed probe B had run it end to end — that was a throwaway that was
    never committed, which is the fourth time in this lane a claim rested on
    something not in the tree."""
    run = run_decision_record(build_kl_with_both(), INITIAL_NO_INCOME, request_id="dr-run2")
    assert run.value_of(DS_FILING_VERDICT) == VERDICT_NOT_DETERMINED
    record = run.value_of(DS_GROSS_INCOME_ORIGIN)
    assert record[FIELD_REFUSAL_REASON] == REFUSAL_FIELD_ABSENT
    assert record[FIELD_ADMITTED] is False


def test_run_2_the_refusal_is_graph_resident_and_names_the_missing_item():
    """**G4's reading half.** The plan's acceptance for run 2 is that the
    refusal is *graph-resident* and *names the missing item in prose* — both
    asserted structurally here rather than by string-matching a rendering."""
    run = run_decision_record(build_kl_with_both(), INITIAL_NO_INCOME, request_id="dr-run2b")
    graph = run.graph
    produced = _instances(
        graph, NODE_TYPE_DATASTATE_INSTANCE, PROP_DATASTATE_INSTANCE_TYPE,
        DS_GROSS_INCOME_ORIGIN,
    )
    assert len(produced) == 1, "the refusal must be IN the graph, not beside it"
    detail = run.value_of(DS_GROSS_INCOME_ORIGIN)["refusal_detail"]
    assert "their filed return" in detail and ":" not in detail


def test_run_2_the_income_instance_exists_and_carries_nothing():
    """A refused value is present-and-empty, never absent. A missing instance
    and a refused one are different facts and a Record must not confuse them —
    which is also why ``value_of`` raises rather than returning None."""
    run = run_decision_record(build_kl_with_both(), INITIAL_NO_INCOME, request_id="dr-run2c")
    assert run.value_of(DS_GROSS_INCOME) is None


def test_run_3_a_gap_in_the_policy_set_still_produces_a_record():
    run = run_decision_record(build_kl(EDITION_2023), INITIAL_UNCOVERED)
    assert run.value_of(DS_FILING_VERDICT) == VERDICT_NOT_DETERMINED
    record = run.value_of(DS_FILING_THRESHOLD_ORIGIN)
    assert record[FIELD_ADMITTED] is False
    assert record[FIELD_REFUSAL_REASON] == REFUSAL_NO_SOURCE_IN_FORCE


def test_an_outage_stops_the_run_and_leaves_no_verdict():
    """L-2 through the L4 path. ``execution.run`` marks the PipelineRun failed
    and the terminal node names the capacity that stopped it — so even a run
    that produced nothing is renderable."""
    run = run_decision_record(None, INITIAL_2024, request_id="dr-outage")
    graph = run.graph
    assert graph is not None, "an outage must still leave a graph, or L-2 bought nothing"
    assert _instances(
        graph, NODE_TYPE_CAPACITY_INSTANCE, PROP_CAPACITY_INSTANCE_TYPE, CAP_DECISION
    ) == []
    with pytest.raises(AssertionError):
        run.value_of(DS_FILING_VERDICT)
    stopped = [n for n in graph.nodes.values() if n.type_name == NODE_TYPE_RUN_STOPPED]
    assert len(stopped) == 1
    assert stopped[0].value == RUN_STOPPED_STEP_FAILED
    detail = str((stopped[0].properties or {}).get(PROP_RUN_STOPPED_DETAIL))
    assert POLICY_PHRASE in detail
    assert "source_unreachable" not in detail, (
        "stopped_detail is printed by a Decision Record; the refusal token "
        "lives on PolicyStoreUnreachableError.refusal_reason, not in the text"
    )


def test_a_single_start_plan_raises_rather_than_under_wiring():
    """Why two starts, stated as a behaviour — and it is RUN 4's shape.

    One start selects ``BFSFinder`` by arity, the as-of date is unreachable from
    the document, and BFS returns ``bfs_exhausted``: **not found at all**, not a
    route with an input silently dropped. That distinction is the correction the
    day-one probe made to the slice plan and it still holds through L4.

    What is new here, and what the plan did not say: ``execution.run`` **raises**
    ``LeafPipelineNotFound``. It does not fall back to the notional record. So an
    unfindable route leaves **no grounding graph at all** — no `RunStopped`, no
    instances, nothing for a renderer to read. That is precisely why run 4 needs
    a pre-minted root, and precisely why pre-minting belongs to run 4 rather
    than to this item: here it would duplicate a seeded start, there it is the
    only thing that would exist.
    """
    from mindsos_intelligence.execution import LeafPipelineNotFound

    plan = decision_record_plan(starts=(DS_FILING_RECORD,))
    with pytest.raises(LeafPipelineNotFound) as excinfo:
        run_decision_record(
            build_kl_with_both(),
            {DS_FILING_RECORD: INITIAL_2024[DS_FILING_RECORD]},
            plan=plan,
        )
    assert "bfs_exhausted" in str(excinfo.value)
