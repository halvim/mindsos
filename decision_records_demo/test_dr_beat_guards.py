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
    for shape in ("claim", "refusal", "outage", "boundary", "noroute"):
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
    assert closer_ref({"routing": "r1", "settlement": "s1"}) == ("settlement", "s1")


if __name__ == "__main__":
    for fn in sorted(
        (v for k, v in list(globals().items()) if k.startswith("test_")),
        key=lambda f: f.__name__,
    ):
        fn()
        print(f"PASS {fn.__name__}")
