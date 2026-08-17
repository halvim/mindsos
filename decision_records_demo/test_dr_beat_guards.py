"""Guards on the per-beat runner — three ways it could become a slideshow.

The runner exists so the script can be PERFORMED: one beat, live, on cue.
Each guard below names a way it could quietly stop being that while still
printing something that looks right in a room.

No FalkorDB, no docker: the beat map, the memo and the closer's precondition
are all decidable without a store, which is why they can be guarded at all.

    PYTHONPATH=. python decision_records_demo/test_dr_beat_guards.py
"""

from __future__ import annotations

import os
import tempfile

from decision_records_demo.dr_demo_beat import (
    BEATS,
    CLOSER_PREFERENCE,
    BeatError,
    beat,
    closer_ref,
    memo_read,
    memo_write,
    remember,
)
from decision_records_demo.dr_render_pages import CASES


def test_every_scripted_beat_has_a_runner():
    """Beats 1-6 are the script's shown beats (0 and 7 are spoken). Every
    one must resolve, and every case it names must EXIST in the demo's own
    case table — checked against `dr_render_pages.CASES`, not against a list
    this file keeps, so a renamed case reddens here instead of failing in
    front of the room."""
    assert sorted(BEATS) == [1, 2, 3, 4, 5, 6], sorted(BEATS)
    named = []
    for number in sorted(BEATS):
        spec = beat(number)
        assert spec.title.strip(), f"beat {number} has no title"
        for case in spec.cases:
            assert case in CASES, (
                f"beat {number} names case {case!r}, which is not in "
                f"dr_render_pages.CASES ({sorted(CASES)})"
            )
            named.append(case)
    assert len(named) >= 5, f"only {len(named)} cases are reachable from a beat"
    # And the split the module exists to record: the mechanism shapes are
    # NOT beats. If one of them ever becomes one, this reddens and the
    # docstring gets rewritten rather than quietly becoming wrong.
    # ⚠ policyprior/policycurrent JOINED this list in ship B: beat 4 now runs
    # the cases that DECIDE against the limit, and the pure lookups stayed as
    # G5's evidence. A case demoted out of the beats and left in the beat map
    # is exactly what this loop exists to catch.
    for shape in ("claim", "refusal", "outage", "boundary", "noroute",
                  "policyprior", "policycurrent"):
        assert shape in CASES, f"{shape!r} vanished from CASES"
        assert shape not in named, f"{shape!r} is a mechanism shape, not a beat"
    try:
        beat(7)
    except BeatError:
        return
    raise AssertionError("beat 7 is spoken and must not resolve to a runner")


def test_the_beat_memo_holds_refs_never_pages():
    """D9 in code. The only thing carried between beats is a graph id; the
    moment the memo can hold a rendered page, beat 6 can PRINT something it
    saved instead of something the store rebuilt, and the reconstructibility
    claim becomes theatre."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "memo.json")
        remember("routing", "capacityrunindex:drdemo-1", path)
        assert memo_read(path) == {"routing": "capacityrunindex:drdemo-1"}
        page = "Decision Record — claim CLM-3007\nDecided 2026-08-17\n"
        for bad in (page, "two words", ""):
            try:
                memo_write({"routing": bad}, path)
            except BeatError:
                continue
            raise AssertionError(f"the memo accepted {bad!r}")
        assert memo_read(path) == {"routing": "capacityrunindex:drdemo-1"}, (
            "a refused write still changed the memo on disk"
        )


def test_the_closer_refuses_when_no_beat_has_run():
    """Beat 6 rebuilds what the room already watched being produced. With an
    empty memo there is no such Record, and a fallback would rebuild one from
    a different meeting — worse than stopping, because it looks identical."""
    try:
        closer_ref({})
    except BeatError as exc:
        assert "no beat has run" in str(exc), exc
    else:
        raise AssertionError("the closer invented a Record to rebuild")
    # With beats run, the closer prefers a Record the room saw produced.
    assert closer_ref({"routing": "r1"}) == ("routing", "r1")
    # ⚠ INVERTED BY SHIP B SLICE 2 (walk gap 5). This line asserted that
    # settlement won over routing, which is the defect the walk found: the
    # closer rebuilt the weakest page in the demo.
    assert closer_ref({"routing": "r1", "settlement": "s1"}) == ("routing", "r1")


def test_the_closer_rebuilds_the_richest_record_the_room_watched():
    """WALK GAP 5, ship B slice 2. Beat 6's argument is *"every line
    traces"*, so it must rebuild the page with the most lines that trace —
    the routing refusal (four exposures, three verdicts, a refusal at its
    position, and a therefore that names what it could not assign), never
    settlement (three lines, no decision).

    Every position in the order is exercised, not just the pair the walk
    happened to look at: a one-line preference change that satisfied the
    walk's example while leaving position three wrong would pass a guard
    written to the example."""
    memo = {"routingrefusal": "rr", "routing": "r1", "settlement": "s1"}
    assert closer_ref(memo) == ("routingrefusal", "rr")
    assert closer_ref({"routing": "r1", "settlement": "s1"}) == ("routing", "r1")
    assert closer_ref({"settlement": "s1"}) == ("settlement", "s1")
    # And the tail: a case outside the preference still rebuilds rather than
    # raising — the closer refuses only when NOTHING has run.
    assert closer_ref({"policyprior": "p1"}) == ("policyprior", "p1")


def test_every_closer_preference_is_a_case_a_beat_actually_runs():
    """A typo in the preference does not fail — it silently DEMOTES that
    entry, and the closer falls through to `sorted(memo)[0]` in front of the
    room. The order is only load-bearing while every name in it is a case
    some beat writes to the memo, so both halves are checked here."""
    runnable = {case for spec in BEATS.values() for case in spec.cases}
    for name in CLOSER_PREFERENCE:
        assert name in CASES, f"{name!r} is not a case in dr_render_pages.CASES"
        assert name in runnable, (
            f"{name!r} is preferred by the closer but no beat runs it, so it "
            f"can never be in the memo (beats run {sorted(runnable)})"
        )


if __name__ == "__main__":
    for fn in sorted(
        (v for k, v in list(globals().items()) if k.startswith("test_")),
        key=lambda f: f.__name__,
    ):
        fn()
        print(f"PASS {fn.__name__}")
