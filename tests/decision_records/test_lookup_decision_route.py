"""The route: found by the finder, executed through ``execute_pipeline``,
grounded in ``capacity_mm``.

**Not a script calling capacities in order, and not a hand-assembled
Pipeline.** ``BRAIN_ARCHITECTURE_AUDIT.md`` records arc1 registering a
1,032-line capacity topology over a solver that never executed through it; a
hand-wired slice reproduces that exactly and every downstream number becomes a
claim about something that did not happen.

Dispatch is the **real** ``L4Dispatcher`` throughout, not a fake. The one thing
nothing had ever done is have a capacity body read L2 through ``context.kl`` —
``dispatch.py`` says so in a comment — so a fake dispatcher here would leave the
riskiest part of the design untested and hand the discovery to the run driver.

Guards **G7** and **G8′** are re-homed here from
``tests/decision_records/test_route_probe.py``. The probe is a diagnostic marked
for deletion the day L4 gains plural-start expressiveness; deleting it must not
silently delete two guards with it.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import ConjunctionFinder
from mindsos_capacity.builtins.origin_v0 import (
    FIELD_ADMITTED,
    FIELD_REFUSAL_REASON,
    FIELD_SOURCE_VERSION,
    REFUSAL_NO_SOURCE_IN_FORCE,
)
from mindsos_capacity.identifiers import (
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    EDGE_STOPPED_AT,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    NODE_TYPE_RUN_STOPPED,
    PROP_CAPACITY_INSTANCE_TYPE,
    PROP_DATASTATE_INSTANCE_TYPE,
    PROP_RUN_STOPPED_DETAIL,
    RUN_STOPPED_STEP_FAILED,
)
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline

from ._dr_fixtures import (
    CAP_DECISION,
    CAP_LOOKUP,
    CAP_READER,
    DS_FILING_THRESHOLD,
    DS_FILING_THRESHOLD_ORIGIN,
    DS_FILING_VERDICT,
    DS_GROSS_INCOME,
    EDITION_2023,
    INITIAL_2023,
    INITIAL_2024,
    INITIAL_UNCOVERED,
    POLICY_PHRASE,
    STARTS,
    VERDICT_MUST_FILE,
    VERDICT_NOT_DETERMINED,
    build_capacity_layer,
    build_kl,
    build_kl_with_both,
)


def _find(cl, session):
    return ConjunctionFinder().find(
        cl,
        session=session,
        start_datastates=STARTS,
        target_datastate=DS_FILING_VERDICT,
    )


def _run(kl, initial, *, run_ref="pipelinerun:dr-1"):
    cl, session = build_capacity_layer()
    verdict = _find(cl, session)
    assert verdict.found, (
        f"no route from {sorted(STARTS)} to the filing verdict: "
        f"{getattr(verdict, 'reason', None)} / {getattr(verdict, 'detail', None)}"
    )
    mm = MentalModel(session_id=session.session_id, user_id=session.user_id)
    dispatcher = L4Dispatcher(cl, session=session, kl=kl)
    result = execute_pipeline(
        dispatcher,
        verdict.pipeline,
        initial,
        request_id="dr-route",
        mm=mm,
        pipeline_run_ref=run_ref,
    )
    return cl, session, verdict.pipeline, result


def _instances(graph, type_name, prop, value):
    return [
        n
        for n in graph.nodes.values()
        if n.type_name == type_name and (n.properties or {}).get(prop) == value
    ]


# ── composition ───────────────────────────────────────────────────────


def test_the_finder_composes_the_route_from_two_starts():
    cl, session = build_capacity_layer()
    verdict = _find(cl, session)
    assert verdict.found
    composed = [s.capacity_iri for s in verdict.pipeline.steps]
    assert set(composed) == {CAP_READER, CAP_LOOKUP, CAP_DECISION}


def test_the_criterion_is_wired_to_both_of_its_producers():
    cl, session = build_capacity_layer()
    pipeline = _find(cl, session).pipeline
    step = next(s for s in pipeline.steps if s.capacity_iri == CAP_DECISION)
    assert set(step.input_datastates) == {DS_GROSS_INCOME, DS_FILING_THRESHOLD}
    idx = {s.capacity_iri: i for i, s in enumerate(pipeline.steps)}
    incoming = {
        e.datastate for e in pipeline.edges if e.consumer == idx[CAP_DECISION]
    }
    assert incoming == {DS_GROSS_INCOME, DS_FILING_THRESHOLD}


def test_the_lookup_appears_exactly_once():
    """Core defect D-E: a capacity reached twice while a pipeline is under
    construction is appended twice, and ``execute_pipeline`` then runs it twice
    with a one-slot blackboard silently overwriting the first result."""
    cl, session = build_capacity_layer()
    pipeline = _find(cl, session).pipeline
    assert [s.capacity_iri for s in pipeline.steps].count(CAP_LOOKUP) == 1


# ── the clean run ─────────────────────────────────────────────────────


def test_the_route_runs_and_reaches_the_verdict():
    _, _, _, result = _run(build_kl_with_both(), INITIAL_2024)
    assert result.success, f"failed at {result.failed_step}: {result.error}"
    assert result.outputs[DS_FILING_VERDICT] == VERDICT_MUST_FILE
    assert result.outputs[DS_FILING_THRESHOLD] == 29200


def test_the_body_read_the_store_through_the_real_dispatcher_context():
    """The first capacity body to read L2 through ``context.kl``.

    Nothing had done it before — every pipeline in ``tests/llm_seam`` is
    hand-built and the route probe's dispatcher passes no context at all. If
    ``L4Dispatcher.build_context`` did not carry a usable read surface, the
    limit below would be ``None`` and the verdict would be *not determined*.
    """
    _, _, _, result = _run(build_kl_with_both(), INITIAL_2024)
    assert result.outputs[DS_FILING_THRESHOLD] == 29200
    assert result.outputs[DS_FILING_THRESHOLD_ORIGIN][FIELD_ADMITTED] is True


def test_the_derivation_is_in_the_graph_not_beside_it():
    """The acceptance gate in miniature: the two values the money sentence
    names each have a CONSUMES edge into the criterion's own CapacityInstance,
    from the instance that produced them."""
    _, _, _, result = _run(build_kl_with_both(), INITIAL_2024)
    graph = result.capacity_graph
    assert graph is not None

    decisions = _instances(
        graph, NODE_TYPE_CAPACITY_INSTANCE, PROP_CAPACITY_INSTANCE_TYPE, CAP_DECISION
    )
    assert len(decisions) == 1
    consumed = set()
    for edge in graph.edges.values():
        if edge.type_name != EDGE_CONSUMES:
            continue
        if edge.target.node_id != decisions[0].node_id:
            continue
        assert edge.source.type_name == NODE_TYPE_DATASTATE_INSTANCE
        consumed.add((edge.source.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE))
    assert consumed == {DS_GROSS_INCOME, DS_FILING_THRESHOLD}


def test_the_origin_record_is_produced_by_the_lookup_that_read_it():
    """Provenance is not a field somebody attached — it is an edge from the
    invocation that obtained it."""
    _, _, _, result = _run(build_kl_with_both(), INITIAL_2024)
    graph = result.capacity_graph
    lookups = _instances(
        graph, NODE_TYPE_CAPACITY_INSTANCE, PROP_CAPACITY_INSTANCE_TYPE, CAP_LOOKUP
    )
    assert len(lookups) == 1
    produced = {
        (e.target.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)
        for e in graph.edges.values()
        if e.type_name == EDGE_PRODUCES and e.source.node_id == lookups[0].node_id
    }
    assert produced == {DS_FILING_THRESHOLD, DS_FILING_THRESHOLD_ORIGIN}


def test_g7_the_parentless_values_are_exactly_the_declared_starts():
    """G7, re-homed. Catches the real failure: a value that should have been
    derived arriving via ``seed()``, which mints with no incoming edge and is
    permanently unattributable."""
    _, _, _, result = _run(build_kl_with_both(), INITIAL_2024)
    graph = result.capacity_graph
    has_incoming = {e.target.node_id for e in graph.edges.values()}
    parentless = {
        (n.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)
        for n in graph.nodes.values()
        if n.type_name == NODE_TYPE_DATASTATE_INSTANCE
        and n.node_id not in has_incoming
    }
    assert parentless == set(STARTS)


def test_g8_prime_nothing_is_registered_global():
    """G8′ — a **gap-pin, not a guard**, and the same class as
    ``test_append_only_is_declared_but_not_enforced``. It pins the all-Local
    reality ``core-datastate-realm-free`` forces on the capacities, so the day
    realms move the union view's shadow-not-merge rule cannot swap the
    authority underneath us. **Delete it the day DataStates go realm-free.**
    """
    cl, _ = build_capacity_layer()
    global_view = cl.global_view()
    for iri in (CAP_LOOKUP, CAP_DECISION, CAP_READER):
        assert global_view.get_capacity(iri) is None


def test_two_dates_over_one_store_produce_two_limits_and_two_versions():
    """Run 5 end to end. The date is a start DataState, so this stays "one case
    asked about two dates" instead of "two documents disagreeing"."""
    kl = build_kl_with_both()
    _, _, _, old = _run(kl, INITIAL_2023, run_ref="pipelinerun:dr-2023")
    _, _, _, new = _run(kl, INITIAL_2024, run_ref="pipelinerun:dr-2024")
    assert (old.outputs[DS_FILING_THRESHOLD], new.outputs[DS_FILING_THRESHOLD]) == (
        27700,
        29200,
    )
    assert old.outputs[DS_FILING_THRESHOLD_ORIGIN][FIELD_SOURCE_VERSION] == "2023.1"
    assert new.outputs[DS_FILING_THRESHOLD_ORIGIN][FIELD_SOURCE_VERSION] == "2024.1"


# ── the two refusals, end to end ──────────────────────────────────────


def test_a_gap_in_the_policy_set_still_produces_a_record():
    """Run 3. The lookup returns rather than raising, so the run completes, the
    criterion refuses to guess, and the reason is on the graph in the limit's
    origin record — where a renderer reads it."""
    _, _, _, result = _run(build_kl(EDITION_2023), INITIAL_UNCOVERED)
    assert result.success
    assert result.outputs[DS_FILING_VERDICT] == VERDICT_NOT_DETERMINED

    graph = result.capacity_graph
    origins = _instances(
        graph,
        NODE_TYPE_DATASTATE_INSTANCE,
        PROP_DATASTATE_INSTANCE_TYPE,
        DS_FILING_THRESHOLD_ORIGIN,
    )
    assert len(origins) == 1
    assert origins[0].value[FIELD_REFUSAL_REASON] == REFUSAL_NO_SOURCE_IN_FORCE
    assert origins[0].value[FIELD_ADMITTED] is False


def test_g3_an_unreadable_store_leaves_no_verdict_and_says_which_step_stopped():
    """G3 and L-2 together. The criterion never ran, so nothing may claim it
    did; and the run is still renderable, because the terminal node names the
    capacity that stopped it."""
    cl, session = build_capacity_layer()
    pipeline = _find(cl, session).pipeline
    mm = MentalModel(session_id=session.session_id, user_id=session.user_id)
    result = execute_pipeline(
        L4Dispatcher(cl, session=session, kl=None),
        pipeline,
        INITIAL_2024,
        request_id="dr-outage",
        mm=mm,
        pipeline_run_ref="pipelinerun:dr-outage",
    )
    assert not result.success
    assert result.failed_step == CAP_LOOKUP
    assert DS_FILING_VERDICT not in result.outputs

    graph = result.capacity_graph
    assert (
        _instances(
            graph,
            NODE_TYPE_CAPACITY_INSTANCE,
            PROP_CAPACITY_INSTANCE_TYPE,
            CAP_DECISION,
        )
        == []
    )
    stopped = [
        n for n in graph.nodes.values() if n.type_name == NODE_TYPE_RUN_STOPPED
    ]
    assert len(stopped) == 1
    assert stopped[0].value == RUN_STOPPED_STEP_FAILED
    detail = str((stopped[0].properties or {}).get(PROP_RUN_STOPPED_DETAIL))
    assert POLICY_PHRASE in detail
    assert "source_unreachable" not in detail, (
        "stopped_detail is printed by a Decision Record; the refusal token "
        "lives on PolicyStoreUnreachableError.refusal_reason, not in the text"
    )
    stopped_at = [
        e
        for e in graph.edges.values()
        if e.type_name == EDGE_STOPPED_AT and e.source.node_id == stopped[0].node_id
    ]
    assert len(stopped_at) == 1
    assert (stopped_at[0].target.properties or {})[
        PROP_CAPACITY_INSTANCE_TYPE
    ] == CAP_LOOKUP
