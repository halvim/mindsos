"""Beat 4's guards: the page DECIDES something against the dated limit.

The walk of 2026-08-17 found beat 4 showing two lookups under a heading that
says *Decision Record*. These guards are the ways that could quietly come
back while the page still looks right in a room.

Run under pytest, or with no dependencies at all:

    PYTHONPATH=. python decision_records_demo/test_dr_assessment_guards.py
"""

from __future__ import annotations

import re

from mindsos_intelligence import execution

from decision_records_demo.dr_assessment import (
    CASE_ASSESSED_CURRENT,
    CASE_ASSESSED_PRIOR,
    DS_ASSESSED_CLAIM,
    DS_CLAIMED_AMOUNT,
    DS_DWELLING_LIMIT,
    DETERMINED_BY,
    _assess,
    assessment_harness,
    assessment_plan,
)
from decision_records_demo.dr_render import (
    G6_BANNED,
    render_from_graphs,
)

EPISODE_COMPLETED = {
    "capacity_root_ref": "unused-by-render_from_graphs",
    "consolidated_at": "2026-08-15T12:00:00.000000+00:00",
    "outcome_classification": "completed",
}


def _graphs(claim, *editions):
    mm, dispatcher, writer, request_run = assessment_harness(*editions)
    graphs: list = []
    execution.run(
        dispatcher, writer, assessment_plan(), request_run, mm=mm,
        solve_seed={DS_ASSESSED_CLAIM: dict(claim)},
        capacity_graphs=graphs,
        case_label="claim CLM-4188",
    )
    return graphs


def _page(claim, *editions):
    return render_from_graphs(_graphs(claim, *editions), EPISODE_COMPLETED)


def _g6_clean(page):
    low = page.lower()
    for token in G6_BANNED + ("drdemo_",):
        assert token not in low, f"G6: {token!r} leaked:\n{page}"


def test_beat4_page_carries_a_decision_not_two_lookups():
    """WALK GAP 2. Before ship B this page was a date in and a limit out
    under a heading that says Decision Record. It now states what the policy
    pays, in the capacity's own registered phrase."""
    page = _page(CASE_ASSESSED_PRIOR)
    assert "assessing the claimed amount against the limit in force" in page, page
    assert "350000 payable, 50000 above the limit" in page, page
    _g6_clean(page)


def test_the_two_dates_pay_different_amounts_and_name_their_editions():
    """G5's shape, one hop further: two cases differing ONLY in the as-of
    date must now differ in the LIMIT, in what is PAYABLE, and in the edition
    and window each names. A page that changed its number without naming the
    authority that changed is the defect `_source_lines` exists for."""
    prior = _page(CASE_ASSESSED_PRIOR)
    current = _page(CASE_ASSESSED_CURRENT)
    assert "350000 payable, 50000 above the limit" in prior, prior
    assert "375000 payable, 25000 above the limit" in current, current
    assert "version 2023.1" in prior and "2023-12-31" in prior, prior
    assert "version 2024.1" in current and "onwards" in current, current
    assert "2024.1" not in prior and "2023.1" not in current


def test_over_the_limit_the_limit_is_the_deciding_fact():
    """Both inputs were read; only one moved the answer. Over the limit the
    LIMIT is what capped the payment, so the page shows the limit's stored
    question and NOT the amount's."""
    page = _page(CASE_ASSESSED_PRIOR)
    assert "Q. What dwelling coverage limit was in force on 2023-06-01? — 350000." in page, page
    assert "What amount was claimed" not in page, (
        "the amount was read but did not decide, and a page listing every "
        "read is the data dump ship A refused:\n" + page
    )


def test_under_the_limit_the_amount_is_the_deciding_fact():
    """THE TWO-DOOR RULE on the branching predicate this slice adds. A guard
    written only on the over-limit case would pass while the under-limit
    branch credited the wrong input, and the under-limit branch is the one
    the room reaches by lowering the claimed amount live."""
    page = _page(dict(CASE_ASSESSED_PRIOR, claimed_amount=300000))
    assert "300000 payable in full" in page, page
    assert "Q. What amount was claimed on this claim? — 300000." in page, page
    assert "What dwelling coverage limit was in force" not in page, page
    _g6_clean(page)


def test_a_claim_with_no_amount_refuses_in_the_readers_words():
    """The only refusal this decision HAS: one a reader recorded. The claim
    states no amount, the reader refuses in band with its stored words, and
    the page carries those words rather than a verdict."""
    claim = {k: v for k, v in CASE_ASSESSED_PRIOR.items() if k != "claimed_amount"}
    page = _page(claim)
    assert "Q. What amount was claimed on this claim? — Nothing." in page, page
    assert "the claim as filed does not state an amount claimed" in page, page
    assert "payable" not in page, page
    _g6_clean(page)


def test_what_is_payable_is_arithmetic_on_the_stored_values():
    """Called directly, across the branch. A demo that states a payable
    number the values on screen do not produce fails the FIXTURE-DESIGN RULE
    silently — the room does the subtraction and gets a different answer."""
    cases = [
        (400000, 350000, "350000 payable, 50000 above the limit", DS_DWELLING_LIMIT),
        (400000, 375000, "375000 payable, 25000 above the limit", DS_DWELLING_LIMIT),
        (300000, 375000, "300000 payable in full", DS_CLAIMED_AMOUNT),
        (375000, 375000, "375000 payable in full", DS_CLAIMED_AMOUNT),
    ]
    for claimed, limit, expected, decider in cases:
        out = _assess(**{DS_CLAIMED_AMOUNT: claimed, DS_DWELLING_LIMIT: limit})
        verdict = list(out.values())[0]
        assert verdict["decision"] == expected, (claimed, limit, verdict)
        assert verdict[DETERMINED_BY] == decider, (claimed, limit, verdict)


def test_the_as_of_date_is_a_read_fact_with_its_own_stored_question():
    """The date is READ from the claim, not seeded beside it, so the store
    holds a question and an answer for it like any other fact. Nothing on the
    page depends on this — which is exactly why it needs a guard: the plan
    could quietly fall back to seeding the date and no page would change."""
    stored = []
    for graph in _graphs(CASE_ASSESSED_PRIOR):
        for node in graph.nodes.values():
            value = node.value
            if isinstance(value, dict) and value.get("question"):
                stored.append(value["question"])
    assert "As of what date is this claim assessed?" in stored, stored
    assert "What amount was claimed on this claim?" in stored, stored


def test_the_deciding_fact_carries_the_authority_behind_it():
    """The source line follows the DECIDING fact, not the conclusion's own
    producer. Same-capacity association is right and it left this page naming
    no edition at all: the limit comes from the lookup, the verdict from the
    capacity that decided against it, and nothing joined them."""
    page = _page(CASE_ASSESSED_PRIOR)
    limit_at = page.find("Q. What dwelling coverage limit was in force")
    source_at = page.find("Source: the dwelling-coverage limit policy, version 2023.1")
    assert limit_at != -1 and source_at != -1, page
    assert limit_at < source_at, page
    assert page.count("Source: the dwelling-coverage limit policy") == 1, (
        "the authority is stated once, not once per association route:\n" + page
    )
    # The other door: a deciding fact with NO policy record behind it prints
    # no Source line, and routing is the case that has one.
    from decision_records_demo.dr_routing import CASE_A_EXPOSURES, routing_harness
    from decision_records_demo.dr_routing import DS_CLAIM_EXPOSURES, routing_plan

    mm, dispatcher, writer, request_run = routing_harness()
    graphs: list = []
    execution.run(
        dispatcher, writer, routing_plan(), request_run, mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: [dict(e) for e in CASE_A_EXPOSURES]},
        capacity_graphs=graphs, case_label="claim CLM-3007",
    )
    assert "Source:" not in render_from_graphs(graphs, EPISODE_COMPLETED)


def test_no_invented_currency_reaches_the_page():
    """CURRENCY FORMATTING IS REFUSED (plan §0.3 item 8): a `$` or a
    thousands separator the layout invents is a fact-channel violation, and
    the unit becomes stored content in v2 rather than chrome. The numbers on
    this page are the ones in the store."""
    for page in (_page(CASE_ASSESSED_PRIOR), _page(CASE_ASSESSED_CURRENT)):
        assert "$" not in page, page
        grouped = re.search(r"\d,\d{3}", page)
        assert grouped is None, f"an invented separator reached the page: {page}"


if __name__ == "__main__":
    import sys

    module = sys.modules[__name__]
    failed = 0
    for name in sorted(n for n in dir(module) if n.startswith("test_")):
        try:
            getattr(module, name)()
            print("PASS " + name)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {exc!r}")
    raise SystemExit(1 if failed else 0)
