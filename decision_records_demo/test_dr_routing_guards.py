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
    assert "Q." not in page, "no refusal in case A; Q. must be earned"
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
    laurent_at = page.find("D. Laurent")
    q_at = page.find("Q. What injury severity")
    mensah_at = page.find("C. Mensah")
    assert mensah_at < laurent_at < q_at, "the refusal block sits in place"
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


if __name__ == "__main__":
    for fn in sorted(
        (v for k, v in list(globals().items()) if k.startswith("test_")),
        key=lambda f: f.__name__,
    ):
        fn()
        print(f"PASS {fn.__name__}")
