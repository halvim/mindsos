"""Routing-content guards: beat 1 renders two desks from one claim, beat 2
renders a refusal BESIDE answers with the missing item named from the stored
record, and the ADR-0209 static decode check fires on this module's own road.

Run under pytest, or with no dependencies at all:

    PYTHONPATH=. python decision_records_demo/test_dr_routing_guards.py
"""

from __future__ import annotations

from mindsos_intelligence import execution
from mindsos_intelligence.plan_construction import FoldReducerDecodeError

from decision_records_demo.dr_render import (
    G6_BANNED,
    RendererGapError,
    render_from_graphs,
)
from decision_records_demo.dr_routing import (
    CASE_A_EXPOSURES,
    DETERMINED_BY,
    DS_COVERAGE,
    DS_SEVERITY,
    CASE_B_EXPOSURES,
    DS_CLAIM_EXPOSURES,
    ROUTINE_DESK,
    SPECIALTY_UNIT,
    routing_harness,
    routing_plan,
)

EPISODE_COMPLETED = {
    "capacity_root_ref": "unused-by-render_from_graphs",
    "consolidated_at": "2026-08-15T12:00:00.000000+00:00",
    "outcome_classification": "completed",
}


def _routing_graphs(exposures, **harness_kw):
    mm, dispatcher, writer, request_run = routing_harness(**harness_kw)
    graphs: list = []
    execution.run(
        dispatcher, writer, routing_plan(), request_run, mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: [dict(e) for e in exposures]},
        capacity_graphs=graphs,
        case_label="claim CLM-3007",
    )
    return graphs


def _g6_clean(page):
    low = page.lower()
    for token in G6_BANNED + ("drdemo_",):
        assert token not in low, f"G6: {token!r} leaked:\n{page}"


def test_case_a_one_claim_two_desks():
    """Beat 1: three exposures, one document, two desks — a member block per
    exposure and the claim-level assignment line, in buyer words only."""
    page = render_from_graphs(_routing_graphs(CASE_A_EXPOSURES), EPISODE_COMPLETED)
    assert page.count(ROUTINE_DESK) >= 2
    assert SPECIALTY_UNIT in page
    assert "A. Silva" in page and "B. Osei" in page and "C. Mensah" in page
    assert "choosing the desk for one exposure → the routine claims desk" in page, (
        "the verdict line wears the DECISION's phrase, not a reader's"
    )
    assert "Therefore: assigning each exposure to its desk" in page
    assert "2 exposure(s) to the routine claims desk" in page
    assert "1 to the specialty injury unit" in page
    assert (
        "Q. Which coverage was this exposure filed under? — Auto Physical Damage."
        in page
    ), "a vehicle exposure routes on coverage, and the page says so"
    assert (
        "Q. What injury severity was assessed for this exposure? — severe."
        in page
    ), "the injury exposure was decided by its severity, and the page says so"
    assert page.count("Q. Which coverage") == 2, (
        "exactly the two vehicle exposures show the coverage question — "
        "C. Mensah was decided by severity and must not show it too"
    )
    _g6_clean(page)


def test_case_b_refusal_beside_answers_names_the_item():
    """Beat 2: the same claim plus an injury exposure with no severity
    assessment — the refusal block renders AT ITS POSITION, its words coming
    from the reader's stored origin record (question + the named missing
    item), while every sibling still routes."""
    page = render_from_graphs(_routing_graphs(CASE_B_EXPOSURES), EPISODE_COMPLETED)
    assert (
        "Q. What injury severity was assessed for this exposure? — Nothing. "
        "the intake record for this exposure does not state an injury "
        "severity assessment." in page
    ), page
    assert "D. Laurent" in page, "the refusing exposure's own facts print"
    assert page.count(ROUTINE_DESK) >= 2
    assert SPECIALTY_UNIT in page
    assert "1 cannot be assigned yet" in page
    # ⚠ THE SAME QUESTION IS NOW ON THE PAGE TWICE, and that is the point of
    # beat 2 rather than a collision to work around: C. Mensah's severity was
    # ASSESSED and decided her desk, D. Laurent's was not stated at all. Before
    # the deciding-fact ship this string appeared once, so locating the refusal
    # by the question alone was unambiguous; it is not any more, and a test
    # that kept doing it would silently point at the answered one.
    answered_at = page.find(
        "Q. What injury severity was assessed for this exposure? — severe."
    )
    refused_at = page.find(
        "Q. What injury severity was assessed for this exposure? — Nothing."
    )
    assert answered_at != -1 and refused_at != -1, page
    laurent_at = page.find("D. Laurent")
    mensah_at = page.find("C. Mensah")
    assert mensah_at < answered_at < laurent_at < refused_at, (
        "the same question must read ANSWERED under C. Mensah and UNANSWERED "
        "under D. Laurent, each in its own block:\n" + page
    )
    _g6_clean(page)


def test_the_decode_check_fires_before_any_member_runs():
    """ADR-0209 D4 on this module's own road: a reducer over the
    refusal-capable member set that does NOT declare the decode is refused
    STATICALLY — before any reader or decision body runs."""
    try:
        _routing_graphs(CASE_A_EXPOSURES, decodes_refusals=False)
    except FoldReducerDecodeError:
        return
    raise AssertionError(
        "a non-decoding reducer ran over a refusal-capable member set"
    )


def test_a_member_refusal_with_no_stored_words_raises():
    """The member road refuses to speak a refusal it has no words for. The
    raise has been in the renderer since the routing ship and NOTHING
    exercised it — found 2026-08-16 by removing it and watching every guard
    stay green. Strip the refusing reader\'s origin record and the verdict\'s
    structural marker is all that is left: no question, no detail."""
    graphs = _routing_graphs(CASE_B_EXPOSURES)
    removed = 0
    for graph in graphs:
        # Only the member whose VERDICT refuses: the severity reader also
        # refuses on both vehicle exposures, where it decides nothing (§76 —
        # a vehicle exposure needs no severity). Stripping those would test
        # the noise, not the guard.
        values = [n.value for n in graph.nodes.values()]
        refuses = any(
            isinstance(v, dict)
            and v.get("refusal_reason")
            and "origin_producer_kind" not in v
            for v in values
        )
        if not refuses:
            continue
        for node_id in list(graph.nodes):
            value = graph.nodes[node_id].value
            if (
                isinstance(value, dict)
                and value.get("origin_producer_kind")
                and value.get("refusal_reason")
            ):
                del graph.nodes[node_id]
                for edge_id in [
                    eid for eid, e in graph.edges.items()
                    if e.source.node_id == node_id or e.target.node_id == node_id
                ]:
                    del graph.edges[edge_id]
                removed += 1
    assert removed == 1, f"fixture drifted: removed {removed} records, expected 1"
    try:
        render_from_graphs(graphs, EPISODE_COMPLETED)
    except RendererGapError:
        return
    raise AssertionError("a member refusal with no stored words rendered anyway")



def _member_graphs(graphs):
    """The member graphs (everything but the fold)."""
    return [g for g in graphs if not any(
        isinstance(n.value, list) for n in g.nodes.values()
    )]


def _produced_by(graph, node_id):
    for edge in graph.edges.values():
        if edge.type_name == "PRODUCES" and edge.target.node_id == node_id:
            return edge
    return None


def _find(graph, ds_type):
    for node_id, node in graph.nodes.items():
        if (node.properties or {}).get("datastate_type") == ds_type:
            return node_id, node
    return None, None


def test_only_the_deciding_read_reaches_the_page():
    """THE RULING, 2026-08-17: the page shows the fact that DECIDED, not every
    fact read. C. Mensah's exposure was read for BOTH coverage and severity —
    both admitted, both stored — and only the severity decided the desk. The
    coverage question must be absent from that block, or the page is a data
    dump and the room stops following it."""
    page = render_from_graphs(_routing_graphs(CASE_A_EXPOSURES), EPISODE_COMPLETED)
    mensah = page.split("C. Mensah")[1].split("Therefore")[0]
    assert "Q. What injury severity" in mensah, mensah
    assert "Q. Which coverage" not in mensah, (
        "a read that did not decide is on the page: " + mensah
    )


def test_the_determining_marker_never_reaches_the_page():
    """The marker names a DataState, so it is branch-only — it SELECTS which
    stored question to print and must never appear. Same discipline as
    ``refusal_reason`` (ADR-0209)."""
    page = render_from_graphs(_routing_graphs(CASE_A_EXPOSURES), EPISODE_COMPLETED)
    assert DETERMINED_BY not in page, page
    assert DS_COVERAGE not in page and DS_SEVERITY not in page, page
    _g6_clean(page)


def test_a_declared_deciding_fact_with_no_stored_question_raises():
    """G2 on the new surface: the verdict NAMES the input that decided it, so
    the question behind that input must be in the run's evidence. Strip the
    reader's origin record and the page must raise rather than print a verdict
    whose stated reason it cannot show."""
    graphs = _routing_graphs(CASE_A_EXPOSURES)
    removed = 0
    for graph in _member_graphs(graphs):
        node_id, _ = _find(graph, DS_COVERAGE + "_origin")
        if node_id is None:
            continue
        del graph.nodes[node_id]
        for eid in [e for e, edge in graph.edges.items()
                    if edge.source.node_id == node_id or edge.target.node_id == node_id]:
            del graph.edges[eid]
        removed += 1
        break
    assert removed == 1, f"fixture drifted: removed {removed}, expected 1"
    try:
        render_from_graphs(graphs, EPISODE_COMPLETED)
    except RendererGapError:
        return
    raise AssertionError("a verdict rendered a reason it could not show")


def test_a_question_and_an_answer_from_different_capacities_raise():
    """Pairing is by NAME (`<value>_origin`) and CROSS-CHECKED by producing
    capacity. The name link alone would let a question print over an answer
    another capacity produced — incoherent, not ambiguous, so it raises rather
    than preferring one. This is the neighbourhood the correlation bijection's
    two silent omissions lived in."""
    graphs = _routing_graphs(CASE_A_EXPOSURES)
    rewired = 0
    for graph in _member_graphs(graphs):
        rec_id, _ = _find(graph, DS_COVERAGE + "_origin")
        sev_id, _ = _find(graph, DS_SEVERITY + "_origin")
        if rec_id is None or sev_id is None:
            continue
        rec_edge = _produced_by(graph, rec_id)
        sev_edge = _produced_by(graph, sev_id)
        if rec_edge is None or sev_edge is None:
            continue
        rec_edge.source = sev_edge.source
        rewired += 1
        break
    assert rewired == 1, f"fixture drifted: rewired {rewired}, expected 1"
    try:
        render_from_graphs(graphs, EPISODE_COMPLETED)
    except RendererGapError:
        return
    raise AssertionError("a question printed over another capacity's answer")


def test_a_verdict_standing_on_a_refusing_record_raises():
    """A decision that names a determining input whose OWN record does not
    admit the value is incoherent: the reader said it could not read it, and
    the decision claims it decided on it. The page refuses to carry that."""
    graphs = _routing_graphs(CASE_A_EXPOSURES)
    flipped = 0
    for graph in _member_graphs(graphs):
        _, node = _find(graph, DS_COVERAGE + "_origin")
        if node is None or not isinstance(node.value, dict):
            continue
        node.value["admitted"] = False
        flipped += 1
        break
    assert flipped == 1, f"fixture drifted: flipped {flipped}, expected 1"
    try:
        render_from_graphs(graphs, EPISODE_COMPLETED)
    except RendererGapError:
        return
    raise AssertionError("a verdict rendered on a record that refused")


def test_the_field_name_is_spelled_the_same_in_all_three_places():
    """`dr_render` may import neither demo module (G1), so the field is a
    literal in three files. Unpinned, a rename in one would silently stop the
    deciding fact rendering instead of failing — the guard-that-cannot-go-red
    shape. The test may import what the renderer may not."""
    from decision_records_demo import dr_render, dr_routing, dr_settlement

    assert dr_routing.DETERMINED_BY == dr_render.FIELD_DETERMINED_BY
    assert dr_settlement.DETERMINED_BY == dr_render.FIELD_DETERMINED_BY



def test_the_intake_line_does_not_echo_the_deciding_fact():
    """Read live on 2026-08-17 and ruled by the owner: the intake line printed
    every field of the exposure, so the ANSWER to the deciding question stood
    one line above the question asking for it — and Screen A's left panel
    prints the same intake a third time. The deciding fact's value is WHICH
    fact was decisive; the answer was already on screen and read as filler.

    Narrow by design, and this test pins the narrowness in both directions:
    the echoed value goes, and CONTEXT the decision needed but did not state
    stays. C. Mensah keeps *Bodily Injury* and loses only the duplicated
    *severe*."""
    page = render_from_graphs(_routing_graphs(CASE_A_EXPOSURES), EPISODE_COMPLETED)
    silva = page.split("A. Silva")[1].split("B. Osei")[0]
    assert silva.count("Auto Physical Damage") == 1, (
        "the coverage is on Silva's block twice — intake line and deciding "
        "fact:\n" + silva
    )
    assert "Q. Which coverage" in silva, silva
    mensah = page.split("C. Mensah")[1].split("Therefore")[0]
    assert mensah.count("severe") == 1, (
        "the severity is on Mensah's block twice:\n" + mensah
    )
    assert "Bodily Injury" in mensah, (
        "context the decision needed but did not state was dropped with the "
        "echo:\n" + mensah
    )


if __name__ == "__main__":
    for fn in sorted(
        (v for k, v in list(globals().items()) if k.startswith("test_")),
        key=lambda f: f.__name__,
    ):
        fn()
        print(f"PASS {fn.__name__}")
