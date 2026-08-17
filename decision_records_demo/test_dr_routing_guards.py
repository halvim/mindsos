"""Routing-content guards: beat 1 renders two desks from one claim, beat 2
renders a refusal BESIDE answers with the missing item named from the stored
record, and the ADR-0209 static decode check fires on this module's own road.

Run under pytest, or with no dependencies at all:

    PYTHONPATH=. python decision_records_demo/test_dr_routing_guards.py
"""

from __future__ import annotations

import re

from mindsos_intelligence import execution
from mindsos_intelligence.plan_construction import FoldReducerDecodeError

from decision_records_demo.dr_render import (
    G6_BANNED,
    RendererGapError,
    render_from_graphs,
)
from decision_records_demo.dr_routing import (
    CASE_A_EXPOSURES,
    CASE_A_EXPOSURES_2023,
    MEASURED_AGAINST,
    ROUTING_EDITION_2023,
    ROUTING_EDITION_2024,
    DS_THRESHOLD,
    routing_policy_file,
    DETERMINED_BY,
    DS_COVERAGE,
    DS_DESK,
    DS_DESKS,
    DS_EXPOSURE,
    DS_OFF_WORK,
    EXPOSURE_REF,
    CASE_B_EXPOSURES,
    DS_CLAIM_EXPOSURES,
    ROUTINE_DESK,
    SPECIALTY_UNIT,
    _assign,
    routing_harness,
    routing_plan,
)

EPISODE_COMPLETED = {
    "capacity_root_ref": "unused-by-render_from_graphs",
    "consolidated_at": "2026-08-15T12:00:00.000000+00:00",
    "outcome_classification": "completed",
}


def _routing_graphs(exposures, **harness_kw):  # noqa: D401
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
    assert "2 exposures to the routine claims desk" in page
    assert "1 to the specialty injury unit" in page
    assert (
        "Q. Which coverage was this exposure filed under? — Auto Physical Damage."
        in page
    ), "a vehicle exposure routes on coverage, and the page says so"
    assert (
        "Q. How many weeks off work does this exposure state? — 6."
        in page
    ), "the injury exposure was decided by its off-work period, and the page says so"
    assert page.count("Q. Which coverage") == 2, (
        "exactly the two vehicle exposures show the coverage question — "
        "C. Mensah was decided by his off-work period and must not show it twice"
    )
    _g6_clean(page)


def test_case_b_refusal_beside_answers_names_the_item():
    """Beat 2: the same claim plus an injury exposure with no off-work
    assessment — the refusal block renders AT ITS POSITION, its words coming
    from the reader's stored origin record (question + the named missing
    item), while every sibling still routes."""
    page = render_from_graphs(_routing_graphs(CASE_B_EXPOSURES), EPISODE_COMPLETED)
    assert (
        "Q. How many weeks off work does this exposure state? — Nothing. "
        "the intake record for this exposure does not state a "
        "period off work." in page
    ), page
    assert "D. Laurent" in page, "the refusing exposure's own facts print"
    assert page.count(ROUTINE_DESK) >= 2
    assert SPECIALTY_UNIT in page
    assert "1 not yet assigned: D. Laurent, Bodily Injury" in page
    # ⚠ THE SAME QUESTION IS NOW ON THE PAGE TWICE, and that is the point of
    # beat 2 rather than a collision to work around: C. Mensah's off-work was
    # ASSESSED and decided her desk, D. Laurent's was not stated at all. Before
    # the deciding-fact ship this string appeared once, so locating the refusal
    # by the question alone was unambiguous; it is not any more, and a test
    # that kept doing it would silently point at the answered one.
    answered_at = page.find(
        "Q. How many weeks off work does this exposure state? — 6."
    )
    refused_at = page.find(
        "Q. How many weeks off work does this exposure state? — Nothing."
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
        # Only the member whose VERDICT refuses: the off-work reader also
        # refuses on both vehicle exposures, where it decides nothing (§76 —
        # a vehicle exposure needs no off-work period). Stripping those would test
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
    fact read. C. Mensah's exposure was read for coverage, off-work and a date —
    all admitted, all stored — and only the off-work period decided the desk. The
    coverage question must be absent from that block, or the page is a data
    dump and the room stops following it."""
    page = render_from_graphs(_routing_graphs(CASE_A_EXPOSURES), EPISODE_COMPLETED)
    mensah = page.split("C. Mensah")[1].split("Therefore")[0]
    assert "Q. How many weeks off work" in mensah, mensah
    assert "Q. Which coverage" not in mensah, (
        "a read that did not decide is on the page: " + mensah
    )


def test_the_determining_marker_never_reaches_the_page():
    """The marker names a DataState, so it is branch-only — it SELECTS which
    stored question to print and must never appear. Same discipline as
    ``refusal_reason`` (ADR-0209)."""
    page = render_from_graphs(_routing_graphs(CASE_A_EXPOSURES), EPISODE_COMPLETED)
    assert DETERMINED_BY not in page, page
    assert DS_COVERAGE not in page and DS_OFF_WORK not in page, page
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
    except RendererGapError as exc:
        # ⚠ Was a bare `except RendererGapError` — §94 finding 5's shape in a
        # guard that predates it: it could not tell its own gap from any other
        # raise on this path. Named in coordination §101.1, tightened here.
        assert "is not in this run's stored evidence" in str(exc), str(exc)
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
        sev_id, _ = _find(graph, DS_OFF_WORK + "_origin")
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
    # Second literal-in-three-files field, ship B: the words a refusing value
    # carries for what could not be done.
    assert dr_settlement.REFUSAL_PHRASE == dr_render.FIELD_REFUSAL_PHRASE
    from decision_records_demo import dr_assessment

    assert dr_assessment.REFUSAL_PHRASE == dr_render.FIELD_REFUSAL_PHRASE



def test_the_intake_line_does_not_echo_the_deciding_fact():
    """Read live on 2026-08-17 and ruled by the owner: the intake line printed
    every field of the exposure, so the ANSWER to the deciding question stood
    one line above the question asking for it — and Screen A's left panel
    prints the same intake a third time. The deciding fact's value is WHICH
    fact was decisive; the answer was already on screen and read as filler.

    Narrow by design, and this test pins the narrowness in both directions:
    the echoed value goes, and CONTEXT the decision needed but did not state
    stays. C. Mensah keeps *Bodily Injury* and loses only the duplicated
    *6*.

    ⚠ **The first re-cut of this guard counted the bare string `"6"`, which
    also occurs twice inside the as-of date `2026-06-03`** — the exact
    relaxed-substring defect `test_a_short_intake_value_survives_when_it_only_LOOKS_echoed`
    exists to refuse, reintroduced by a mechanical rename in the guard that
    refuses it. **The claim is about the INTAKE LINE**, so the check is now on
    that line alone and on a whole token, not on the block and a substring."""
    page = render_from_graphs(_routing_graphs(CASE_A_EXPOSURES), EPISODE_COMPLETED)
    silva = page.split("A. Silva")[1].split("B. Osei")[0]
    assert silva.count("Auto Physical Damage") == 1, (
        "the coverage is on Silva's block twice — intake line and deciding "
        "fact:\n" + silva
    )
    assert "Q. Which coverage" in silva, silva
    mensah = page.split("C. Mensah")[1].split("Therefore")[0]
    intake = mensah.splitlines()[0]
    assert re.search(r"(?<!\d)6(?!\d)", intake) is None, (
        "the off-work period is echoed on Mensah's intake line, one line above "
        "the question that asks for it:\n" + intake
    )
    assert "— 6." in mensah, (
        "the deciding answer itself went missing with the echo:\n" + mensah
    )
    assert "Bodily Injury" in mensah, (
        "context the decision needed but did not state was dropped with the "
        "echo:\n" + mensah
    )


def _desk_verdicts(graphs):
    """Every desk verdict VALUE the member graphs produced."""
    out = []
    for graph in _member_graphs(graphs):
        for node in graph.nodes.values():
            if (node.properties or {}).get("datastate_type") == DS_DESK:
                out.append(node.value)
    return out


def test_the_claim_line_names_the_pending_exposure():
    """SHIP B SLICE 1 (plan §0.3 item 8 ship B, the §11 promotion out of walk
    gap 6, coordination §91 Q5). The claim-level line said *"1 cannot be
    assigned yet - see the exposure above"* with FOUR exposures above it —
    ambiguous to a cold reader, which is a page defect and not formatting.

    It now names the one it means, in the same words the block above used."""
    page = render_from_graphs(_routing_graphs(CASE_B_EXPOSURES), EPISODE_COMPLETED)
    therefore = page.split("Therefore:")[1]
    assert "1 not yet assigned: D. Laurent, Bodily Injury" in therefore, (
        "the claim line must NAME the exposure it cannot assign, not count "
        "it:\n" + therefore
    )
    assert "see the exposure above" not in page, (
        "the ambiguous phrasing survived somewhere on the page"
    )
    _g6_clean(page)


def test_every_desk_verdict_names_its_exposure_answered_and_refused():
    """THE TWO-DOOR RULE (RULES §12, 2026-08-17) on the branch this slice
    adds. The claim line only needs the name on REFUSED verdicts, so carrying
    it there alone would pass the guard above — and that is exactly the shape
    that produced five of ship A's six findings: a rule unambiguous only while
    its domain has one member.

    Beat 2's case puts both doors in one run: two answered vehicle verdicts,
    one answered injury verdict, one refusal. Every one names its exposure,
    and NONE of them lets the exposure be the fact that decided."""
    verdicts = _desk_verdicts(_routing_graphs(CASE_B_EXPOSURES))
    assert len(verdicts) == 4, verdicts
    answered = [v for v in verdicts if v.get("decision")]
    refused = [v for v in verdicts if v.get("refusal_reason")]
    assert len(answered) == 3 and len(refused) == 1, verdicts
    for verdict in verdicts:
        assert verdict.get(EXPOSURE_REF), (
            "a desk verdict does not name its exposure: " + repr(verdict)
        )
        assert verdict.get(DETERMINED_BY) != DS_EXPOSURE, (
            "the exposure is declared so the decision can NAME it, never so "
            "it can decide: " + repr(verdict)
        )


def test_the_claim_line_is_singular_at_one_and_plural_at_two():
    """The other door of the pluraliser, and the reason the string changed at
    all: *"2 exposure(s)"* read as software on the buyer's screen (walk gap
    6). A hardcoded plural passes the two-exposure case and says
    *"1 exposures"* in the room."""
    two = render_from_graphs(_routing_graphs(CASE_A_EXPOSURES), EPISODE_COMPLETED)
    assert "2 exposures to the routine claims desk" in two, two
    one = render_from_graphs(
        _routing_graphs([CASE_A_EXPOSURES[0], CASE_A_EXPOSURES[2]]),
        EPISODE_COMPLETED,
    )
    assert "1 exposure to the routine claims desk" in one, one
    assert "1 exposures" not in one, one
    _g6_clean(one)


def test_the_exposure_field_name_never_reaches_the_page():
    """Same discipline as the determining marker: the field's VALUE is meant
    for the page, its NAME is not. The field is spelled so that this can be
    asserted — ``exposure_ref`` rather than ``exposure``, which the page says
    in its own words several times."""
    page = render_from_graphs(_routing_graphs(CASE_B_EXPOSURES), EPISODE_COMPLETED)
    assert EXPOSURE_REF not in page, page
    assert "refusal_reason" not in page, page


def test_a_refusing_verdict_with_no_exposure_name_raises():
    """G2's posture — raise, never fill — inside the reducer, and BOTH doors.

    A refusal the record cannot name would silently become *"1 not yet
    assigned: "* or fall back to the count this slice removed. It raises. An
    ANSWERED verdict with no name does not, because the claim line never
    names those and punishing it would be inventing a requirement."""
    anonymous_refusal = {"decision": None, "refusal_reason": "field_absent"}
    try:
        _assign(**{DS_DESKS: [anonymous_refusal]})
    except ValueError:
        pass
    else:
        raise AssertionError(
            "the reducer published a claim line for a refusal it could not name"
        )
    out = _assign(**{DS_DESKS: [{"decision": ROUTINE_DESK}]})
    assert "1 exposure to " + ROUTINE_DESK in str(out), out


# ── step 2: the rule is stored, dated, and SHOWN ───────────────────────

def test_the_routing_rule_is_not_a_literal_in_this_module():
    """Plan §0.4 item 7 step 2's whole point: *without it our side of step iv
    is source code.* The comparison stays; the NUMBER it compares against comes
    out of a dated store. Checked on `_route`'s own source, because a threshold
    that crept back as a constant would still pass every page assertion below —
    they would just be asserting about a hardcoded 4.

    ⚠ **Checked on the AST, not on the source text.** The first version
    scanned characters and reddened on `§76` in a comment — a guard that
    cannot tell a citation from a threshold would have been silenced by
    deleting a comment, which is the worst way for a guard to go green.
    """
    import ast
    import inspect
    import textwrap

    from decision_records_demo import dr_routing

    tree = ast.parse(textwrap.dedent(inspect.getsource(dr_routing._route)))
    numbers = [
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    ]
    assert not numbers, (
        "a numeric literal is back inside the routing decision — the rule "
        f"belongs in the store, and this one does not: {numbers}"
    )


def test_two_editions_route_the_SAME_exposure_to_different_desks():
    """Beat 4's claim, on the routing beats: **which edition governed.** Six
    weeks off work clears the 2024 threshold of four and does NOT clear the
    2023 threshold of eight, so one fixture and two dates produce two desks —
    and each page names the edition that sent him there. Nothing about the
    claim changed; only the rule in force did."""
    now = render_from_graphs(_routing_graphs(CASE_A_EXPOSURES), EPISODE_COMPLETED)
    then = render_from_graphs(_routing_graphs(CASE_A_EXPOSURES_2023), EPISODE_COMPLETED)
    now_block = now.split("C. Mensah")[1].split("Therefore")[0]
    then_block = then.split("C. Mensah")[1].split("Therefore")[0]
    assert SPECIALTY_UNIT in now_block and ROUTINE_DESK in then_block, (
        now_block + "\n----\n" + then_block
    )
    assert "v2024.1" in now_block and "v2023.1" in then_block, (
        "a page decided under an edition it does not name:\n"
        + now_block + "\n----\n" + then_block
    )
    assert "— 6." in now_block and "— 6." in then_block, (
        "the claimant's fact moved between the two runs; only the rule may"
    )


def test_the_page_names_the_rule_it_was_measured_against_and_its_window():
    """**Stored is not shown**, and this is the guard that says so. Found by a
    probe: with the threshold in the store and no rule line, the page named the
    claimant's six weeks and nothing about the policy at all — the lookup ran,
    reached the decision, and never reached the page."""
    page = render_from_graphs(_routing_graphs(CASE_A_EXPOSURES), EPISODE_COMPLETED)
    mensah = page.split("C. Mensah")[1].split("Therefore")[0]
    assert "Q. What off-work threshold" in mensah, mensah
    assert "— 4." in mensah, mensah
    assert "Source: the injury-routing policy, version v2024.1" in mensah, mensah
    assert "in force from 2024-01-01" in mensah, (
        "the edition is named without the window it was in force:\n" + mensah
    )


def test_the_deciding_fact_stays_the_persons_fact_and_the_rule_is_a_second_line():
    """⚠ **The threshold is not the deciding fact.** *"Because he is off work
    six weeks"* is what a room hears; *"because the threshold is four"* is the
    rule. Two structural fields, two lines, and the ORDER is the argument: the
    claimant's fact, then what it was tested against, then where he went."""
    graphs = _routing_graphs(CASE_A_EXPOSURES)
    verdicts = [
        node.value for graph in graphs for node in graph.nodes.values()
        if isinstance(getattr(node, "value", None), dict)
        and node.value.get("decision") == SPECIALTY_UNIT
    ]
    assert verdicts, "no specialty verdict was produced"
    for verdict in verdicts:
        assert verdict.get(DETERMINED_BY) == DS_OFF_WORK, verdict
        assert verdict.get(MEASURED_AGAINST) == DS_THRESHOLD, verdict
    page = render_from_graphs(graphs, EPISODE_COMPLETED)
    mensah = page.split("C. Mensah")[1].split("Therefore")[0]
    fact_at = mensah.find("Q. How many weeks off work")
    rule_at = mensah.find("Q. What off-work threshold")
    verdict_at = mensah.find("choosing the desk")
    assert -1 < fact_at < rule_at < verdict_at, mensah


def test_the_boundary_routes_at_EXACTLY_the_threshold_and_below_it_does_not():
    """Both doors of the comparison the whole ship exists to move into the
    store. Four weeks is the threshold: four goes to the specialty unit, three
    does not. A guard that only exercised six would pass on `>` and on `>=`
    alike."""
    for weeks, desk in ((4, SPECIALTY_UNIT), (3, ROUTINE_DESK)):
        case = [dict(CASE_A_EXPOSURES[2], off_work_weeks=weeks)]
        page = render_from_graphs(_routing_graphs(case), EPISODE_COMPLETED)
        assert desk in page, (weeks, page)


def test_an_exposure_that_consulted_no_rule_cites_none():
    """**A page citing an authority it did not consult is the same defect as a
    renderer composing an outcome word** (§0.3 item 11), one hop further out.

    ⚠ **This guard was first written on the REFUSAL and COULD NOT FAIL.** Its
    mutation reddened nothing: the refusal road never calls ``rule_lines`` at
    all, so D. Laurent's block is rule-free structurally, whatever the verdict
    carries. The claim was right and the SUBJECT was wrong. **A. Silva is where
    it can fail** — a vehicle exposure routes on coverage alone, goes through
    the same member-lines road that renders the rule, and would cite the policy
    the moment the marker appeared on that branch.

    Both are checked, and the refusal is kept as the weaker half rather than
    dropped: it is still true, and its truth now has a stated reason."""
    page = render_from_graphs(_routing_graphs(CASE_B_EXPOSURES), EPISODE_COMPLETED)
    silva = page.split("A. Silva")[1].split("B. Osei")[0]
    assert "the injury-routing policy" not in silva, (
        "an exposure routed on coverage alone cites a rule it never "
        "consulted:\n" + silva
    )
    assert "Q. What off-work threshold" not in silva, silva
    laurent = page.split("D. Laurent")[1].split("Therefore")[0]
    assert "the injury-routing policy" not in laurent, laurent
    assert "Source:" in page, (
        "the fixture stopped citing the policy anywhere, so this guard would "
        "pass on a page that lost the rule line entirely"
    )


def test_no_edition_in_force_REFUSES_IN_BAND_in_the_lookups_own_words():
    """A DIFFERENT refusal from a missing fact, and the distinction is the
    product: the claimant's document was complete and OUR policy set was not.
    `policy_lookup_v0` returns None with its own origin record rather than
    raising, so the page carries the lookup's words and the run stays
    renderable."""
    page = render_from_graphs(
        _routing_graphs(CASE_A_EXPOSURES, editions=(ROUTING_EDITION_2023,)),
        EPISODE_COMPLETED,
    )
    assert SPECIALTY_UNIT not in page, (
        "an exposure routed with no rule in force:\n" + page
    )
    assert "the injury-routing policy" in page, (
        "the page does not say which authority could not be consulted:\n" + page
    )
    assert "not yet assigned: C. Mensah" in page, page


def test_the_policy_FILE_is_stored_words_only():
    """*Printable as the file the model is given* (step 2). Every line of it is
    the edition's own — version, window, threshold, text. A file this lane
    composed out of prose we wrote would be the renderer's-voice defect with a
    filename on it."""
    text = routing_policy_file("2026-06-03")
    assert "v2024.1" in text and "2024-01-01" in text, text
    assert ROUTING_EDITION_2024["text"] in text, text
    assert "8" not in text, ("the 2023 threshold leaked into the 2024 file:\n" + text)
    assert routing_policy_file("2019-01-01") == "", (
        "a file was invented for a date no edition covers"
    )


if __name__ == "__main__":
    for fn in sorted(
        (v for k, v in list(globals().items()) if k.startswith("test_")),
        key=lambda f: f.__name__,
    ):
        fn()
        print(f"PASS {fn.__name__}")
