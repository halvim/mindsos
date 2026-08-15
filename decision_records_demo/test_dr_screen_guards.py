"""Screen guards (coordination §78–§80): the EQUALITY fact guard, the chrome
closures, the CSS-channel lint, the classifier safety pins, the left panel's
verbatim-values rule, and the from-root date-line pin.

Run under pytest, or with no dependencies at all:

    PYTHONPATH=. python decision_records_demo/test_dr_screen_guards.py
"""

from __future__ import annotations

import ast
import os

from mindsos_intelligence import execution

from decision_records_demo.dr_dump import (
    DS_CLAIM_EXPOSURES,
    EXPOSURES,
    _claim_plan,
    _conclude_declaration,
    _decide_declaration,
    _harness,
    _make_flaky_decide,
)
from decision_records_demo.dr_render import G6_BANNED, render_from_graphs
from decision_records_demo.dr_routing import (
    CASE_B_EXPOSURES,
    ROUTINE_DESK,
    SPECIALTY_UNIT,
    routing_harness,
    routing_plan,
)
from decision_records_demo.dr_routing import (
    DS_CLAIM_EXPOSURES as DS_ROUTED_EXPOSURES,
)
from decision_records_demo.dr_screen import (
    CHROME,
    STYLESHEET,
    ScreenGapError,
    StylesheetHiddenError,
    compare_pages,
    compose_screen,
    fact_channel,
    intake_blocks,
    lint_stylesheet,
    page_channel,
    text_nodes,
)

EPISODE = {
    "capacity_root_ref": "unused",
    "consolidated_at": "2026-08-15T12:00:00.000000+00:00",
    "outcome_classification": "completed",
}
EPISODE_STOPPED = dict(EPISODE, outcome_classification="stopped")
DATELESS = dict(EPISODE, consolidated_at="")


def _claim_page(exposures=None, episode=EPISODE):
    mm, dispatcher, writer, request_run = _harness()
    graphs: list = []
    execution.run(
        dispatcher, writer, _claim_plan(), request_run, mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: list(EXPOSURES if exposures is None else exposures)},
        capacity_graphs=graphs, case_label="claim CLM-2041",
    )
    return render_from_graphs(graphs, episode)


def _partial_page():
    mm, dispatcher, writer, request_run = _harness(
        capacities=[
            _decide_declaration(_make_flaky_decide({"A. Silva/contents": 99})),
            _conclude_declaration(),
        ],
    )
    graphs: list = []
    execution.run(
        dispatcher, writer, _claim_plan(), request_run, mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: list(EXPOSURES)},
        capacity_graphs=graphs, case_label="claim CLM-2041",
    )
    return render_from_graphs(graphs, EPISODE_STOPPED)


def _routing_refusal_page():
    mm, dispatcher, writer, request_run = routing_harness()
    graphs: list = []
    execution.run(
        dispatcher, writer, routing_plan(), request_run, mm=mm,
        solve_seed={DS_ROUTED_EXPOSURES: [dict(e) for e in CASE_B_EXPOSURES]},
        capacity_graphs=graphs, case_label="claim CLM-3007",
    )
    return render_from_graphs(graphs, EPISODE)


def test_screen_module_imports_stdlib_only():
    """The layout never grows a graph reader (§79 Q1) — no mindsos_*, no
    demo-module import; the renderer emits any missing text instead."""
    path = os.path.join(os.path.dirname(__file__), "dr_screen.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    allowed = {"__future__", "html", "re", "typing"}
    for node in ast.walk(tree):
        modules = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        for module in modules:
            assert module.split(".")[0] in allowed, (
                f"dr_screen imports {module!r} — the layout must stay "
                "typography over text"
            )


def test_fact_channel_equals_the_page_on_every_known_form():
    """THE guard (§79): chrome-stripped, in order, the styled page's text
    EQUALS the renderer page — drop, reorder, duplicate and invent are all
    one red."""
    for page in (
        _claim_page(),
        _routing_refusal_page(),
        _partial_page(),
        _claim_page([], EPISODE_STOPPED),
    ):
        screen = compose_screen(page, intake=[{"k": "v"}])
        assert fact_channel(screen) == page_channel(page)


def test_refusal_stop_and_therefore_classify_as_themselves():
    """§79 Q3's safety pins: de-emphasising the one line the room must see
    is the presentation sin in CSS form — classifier regression is red."""
    cases = (
        (_routing_refusal_page(), "Q. ", "refusal"),
        (_partial_page(), "Stopped:", "stop"),
        (_claim_page(), "Therefore:", "therefore"),
    )
    for page, prefix, expected in cases:
        screen = compose_screen(page)
        classified = [
            cls for (sec, cls, text) in text_nodes(screen)
            if sec == "record" and text.strip().startswith(prefix)
        ]
        assert classified and set(classified) == {expected}, (
            prefix, classified,
        )


def test_chrome_is_digit_free_and_disjoint_from_the_vocabulary():
    """§79 Q2's closures: assertion-words carry no digits, so vocabulary
    disjointness is the closure that matters. The banned list is COMPUTED
    from the declarations, not recalled."""
    from mindsos_capacity.builtins.origin_v0 import REFUSAL_REASONS
    from mindsos_capacity.identifiers import RUN_STOPPED_PHRASES

    # Function words are NOT assertion words — the §79 closure bans the
    # vocabulary that could smuggle a case fact (desk, payable, injury…),
    # not grammar. "what" earned its place here by colliding with the
    # heading on this guard's FIRST run — the stop phrase "some of what was
    # needed…" put it in the computed set.
    stop_words = {
        "the", "a", "an", "of", "to", "for", "one", "was", "and",
        "this", "from", "so", "no", "-", "is", "be", "not", "in",
        "what", "could", "with", "on", "at", "it", "that", "as", "by",
        "or", "before", "ran", "going", "more", "there",
    }
    vocabulary = set()
    for phrase in (
        ROUTINE_DESK, SPECIALTY_UNIT, "payable",
        *RUN_STOPPED_PHRASES.values(), *REFUSAL_REASONS,
    ):
        vocabulary.update(
            w for w in phrase.lower().replace(",", " ").split()
            if w not in stop_words
        )
    for chrome in CHROME:
        assert not any(ch.isdigit() for ch in chrome), chrome
        chrome_words = set(chrome.lower().split())
        overlap = chrome_words & vocabulary
        assert not overlap, (
            f"chrome {chrome!r} shares vocabulary words {overlap} — an "
            "assertion could smuggle a case fact past the layout"
        )


def test_css_lint_refuses_hiding_and_passes_the_shipped_sheet():
    """§79 Q4-6: the §11 sin by stylesheet. The shipped sheet passes; each
    hiding form is refused; a TRUE-zero font size is refused while the
    legitimate 0.9rem is not (that false positive was hit and fixed in this
    module's own smoke run — pinned so it stays fixed)."""
    lint_stylesheet(STYLESHEET)
    lint_stylesheet("h2 { font-size: 0.9rem; }")
    for bad in (
        "p.refusal { display:none }",
        "p.refusal { display : none }",
        "p.stop { visibility: hidden }",
        "p.stop { font-size: 0 }",
        "p.stop { font-size: 0px }",
    ):
        try:
            lint_stylesheet(STYLESHEET + bad)
        except StylesheetHiddenError:
            continue
        raise AssertionError(f"the lint passed a hiding declaration: {bad}")


def test_left_panel_values_are_the_fixtures_verbatim():
    """§78.3: framing is chrome; every value string on the panel is the
    fixture's own. And the whole screen passes the G6 token scan — the room
    sees words, never machinery."""
    page = _routing_refusal_page()
    intake = [dict(e) for e in CASE_B_EXPOSURES]
    screen = compose_screen(page, intake=intake)
    arrived = fact_channel(screen, section="arrived")
    expected = " ".join(
        " ".join(line.split())
        for block in intake_blocks(intake) for line in block
    )
    assert arrived == expected
    for exposure in intake:
        for value in exposure.values():
            assert str(value) in arrived
    low = screen.lower()
    for token in G6_BANNED + ("drdemo_", "datastate:"):
        assert token not in low, f"{token!r} reached the screen"


def test_a_from_root_page_differs_in_exactly_the_date_line():
    """§79 Q4-5's pin: the live page and the store-alone page differ in ONE
    line — the date present vs the stated absence. Anything else red."""
    live = _claim_page()
    from_root_shaped = _claim_page(episode=DATELESS)
    diffs = compare_pages(live, from_root_shaped)
    assert diffs == [
        ("Decided 2026-08-15",
         "Decided date: not available from stored evidence"),
    ], diffs


def test_a_screen_without_intake_omits_the_panel():
    """The from-root screen: the intake is not store-resident, so the panel
    is ABSENT, never invented — no chrome heading floats over nothing."""
    screen = compose_screen(_claim_page())
    assert 'id="arrived"' not in screen
    assert "What arrived" not in screen


def test_an_empty_page_raises():
    try:
        compose_screen("   \n  ")
    except ScreenGapError:
        return
    raise AssertionError("a screen composed over no page at all")


if __name__ == "__main__":
    for fn in sorted(
        (v for k, v in list(globals().items()) if k.startswith("test_")),
        key=lambda f: f.__name__,
    ):
        fn()
        print(f"PASS {fn.__name__}")
