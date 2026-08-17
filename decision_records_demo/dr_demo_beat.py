"""dr_demo_beat — one beat, live, on cue.

The Gate-7 driver (`dr_demo_run.py`) runs every case in a batch and writes
files. That measures the machine; it cannot perform the script. The demo
script says Screen A shows the Record **as it is produced**, and clicking
through HTML that was rendered this morning while saying that is RULES §11's
sin in a new costume. Beat 6 makes it concrete: the closer is *kill the app,
rerun from the store alone*, which is a command executed in the room and
which no pre-rendered screen can stand in for.

So: a front door onto the case builders that already exist, one beat at a
time, against a store that stands for the length of the meeting.

    PYTHONPATH=. python decision_records_demo/dr_demo_beat.py up
    PYTHONPATH=. python decision_records_demo/dr_demo_beat.py 1
    PYTHONPATH=. python decision_records_demo/dr_demo_beat.py 6
    PYTHONPATH=. python decision_records_demo/dr_demo_beat.py down

**Seven of the twelve cases are not beats.** `claim`, `refusal`, `outage`,
`boundary` and `noroute` are mechanism shapes — evidence that the renderer
stops honestly — and the room never sees them. ⚠ `policyprior` and
`policycurrent` JOINED them in ship B: they are the pure dated lookup, and
beat 4 moved to `assessprior`/`assesscurrent`, which decide something
against the limit those lookups return. The pair stays in `CASES` because
G5's guard is written on it; it is no longer shown. That split was written
nowhere until this module; :data:`BEATS` is now the only place the mapping
lives, and its case names are checked against `dr_render_pages.CASES`
test-side so a rename cannot leave a beat pointing at nothing.

**The memo holds REFS, never PAGES (D9).** Beat 6 re-renders an earlier
beat's Record from the store alone, and the only thing carried between beats
is that beat's ``capacity_root_ref`` — a graph id. :func:`memo_write`
refuses to store anything page-shaped, because the moment the closer can
print something it saved rather than something the store rebuilt, the
reconstructibility claim is theatre and deserves to be called one.

**Gate 4 (the restated form):** this module registers no capacity and no
DataState. No new category beyond ``origin_v0.DECISION_SHAPED_CATEGORIES``,
no new ``FAMILY_RULES`` entry. PASS.

RULES §11 seam: the beat titles, the narration lines and the marker lines
are this module's; everything between BEGIN PAGE and END PAGE is the
renderer's, rendered from the store.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

MEMO_PATH = "/tmp/drdemo-beats.json"
SCREENS_DIR = "/tmp/drdemo-beats"

#: A memo value is a graph id. Anything that looks like a rendered page is
#: refused outright — see the module docstring.
PAGE_TELL = "Decision Record"


class BeatError(RuntimeError):
    """The beat cannot honestly be performed — say so, never improvise."""


@dataclass(frozen=True)
class Beat:
    title: str
    cases: Tuple[str, ...] = ()
    kind: str = "case"


#: The ONLY place the script's beats and the demo's cases are mapped to each
#: other. Beats 0 and 7 are spoken and have no entry.
BEATS: Dict[int, Beat] = {
    1: Beat("One claim, two desks.", ("routing",)),
    2: Beat("The refusal, beside an answer.", ("routingrefusal",)),
    3: Beat("The missing document.", ("settlement",)),
    4: Beat("The policy changed mid-claim.", ("assessprior", "assesscurrent")),
    5: Beat("Unplug the model.", (), kind="guards"),
    6: Beat("A year later.", (), kind="closer"),
}


def beat(number: int) -> Beat:
    if number not in BEATS:
        raise BeatError(
            f"beat {number!r} is not in the script. Beats are "
            f"{sorted(BEATS)}; 0 and 7 are spoken."
        )
    return BEATS[number]


def memo_write(memo: Dict[str, str], path: str = MEMO_PATH) -> None:
    """Persist the beat memo, refusing anything that is not a bare ref."""
    for case, value in memo.items():
        if not isinstance(case, str) or not isinstance(value, str) or not value:
            raise BeatError(
                f"the memo takes case -> ref strings, got {case!r} -> {value!r}"
            )
        if PAGE_TELL in value or any(ch.isspace() for ch in value):
            raise BeatError(
                "the memo may hold a capacity_root_ref and nothing else — "
                "a saved page would make the closer a replay, and D9 rules "
                "that a demo running from saved answers is a scripted demo"
            )
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(memo, fh, indent=1, sort_keys=True)


def memo_read(path: str = MEMO_PATH) -> Dict[str, str]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return dict(json.load(fh))


def remember(case: str, root: str, path: str = MEMO_PATH) -> None:
    memo = memo_read(path)
    memo[case] = root
    memo_write(memo, path)


#: WHICH Record the closer rebuilds, richest page first — walk gap 5, ship B.
#:
#: The walk found beat 6 rebuilding the WEAKEST page: the preference read
#: ``("settlement", "routing")``, and settlement is three lines with no
#: decision, while the routing-refusal page is four exposures, three
#: verdicts, a refusal rendered at its position, and a claim-level therefore
#: that (since slice 1) NAMES the exposure it could not assign. *"Every line
#: traces"* is beat 6's whole argument and it needs lines to trace.
#:
#: It is a NAMED ORDERED CONSTANT rather than a "prefer the strongest page"
#: rule, because "strongest" is an adjective a later ship re-argues. Ship B
#: makes settlement stronger too, so a heuristic would have reopened this
#: question the moment slice 3 lands. The order is a decision; changing it is
#: editing this tuple, and a guard pins every position in it.
#:
#: ⚠ **The trade, stated rather than discovered in a room:** the closer now
#: rebuilds a claim that was NOT fully assigned. That is the stronger story —
#: a year later the Record still says exactly what it could not decide and
#: why — but it is a judgement, and flipping it is one tuple.
CLOSER_PREFERENCE = ("routingrefusal", "routing", "settlement")


def closer_ref(memo: Dict[str, str]) -> Tuple[str, str]:
    """The Record beat 6 rebuilds. NO fallback: if nothing has run, the
    closer says so. A default ref would rebuild a Record from a meeting that
    is not this one, which is worse than stopping."""
    if not memo:
        raise BeatError(
            "no beat has run in this session, so there is no Record to "
            "rebuild. Run beat 1 or 3 first — the closer rebuilds what the "
            "room already watched being produced."
        )
    for preferred in CLOSER_PREFERENCE:
        if preferred in memo:
            return preferred, memo[preferred]
    case = sorted(memo)[0]
    return case, memo[case]


def _client():
    from mindsos_core.config import FalkorConfig
    from mindsos_core.persistence.client import FalkorClient

    return FalkorClient(FalkorConfig.from_env())


def _show(page: str) -> None:
    print("-- BEGIN PAGE --")
    print(page, end="")
    print("-- END PAGE --")


def _run_case(client, name: str, screens_dir: str) -> None:
    from decision_records_demo.dr_render import render_record
    from decision_records_demo.dr_render_pages import (
        CASES, _case_intake, _episode_props,
    )
    from decision_records_demo.dr_screen import compose_screen

    if name not in CASES:
        raise BeatError(f"case {name!r} is not in dr_render_pages.CASES")
    kl, session, episode_id = CASES[name](client)
    props = _episode_props(kl, session, episode_id)
    root = props.get("capacity_root_ref")
    print(f"== case {name} — Episode {episode_id!r}, capacity_root_ref {root!r} ==")
    page = render_record(client, props)
    _show(page)
    if root:
        remember(name, root)
    os.makedirs(screens_dir, exist_ok=True)
    target = os.path.join(screens_dir, f"{name}.html")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(compose_screen(page, intake=_case_intake(name)))
    print(f"screen: {target}")


def _run_guards() -> int:
    """Beat 5 has no case: with no model anywhere, there is nothing to
    unplug. What CAN be shown is the absence, checked live."""
    from decision_records_demo import test_dr_no_model_guards as guards

    print("== the model is not in the decision path, checked now ==")
    for name in sorted(n for n in dir(guards) if n.startswith("test_")):
        getattr(guards, name)()
        print(f"PASS {name}")
    return 0


def _run_closer(client) -> None:
    from decision_records_demo.dr_render import render_record

    case, root = closer_ref(memo_read())
    print(f"== rebuilding {case!r} from the store alone, given only {root!r} ==")
    _show(render_record(client, {"capacity_root_ref": root}))


def main(argv: Sequence[str]) -> int:
    from decision_records_demo.dr_demo_run import DEFAULT_PORT, DockerBackend

    args = list(argv[1:])
    if not args:
        print("usage: dr_demo_beat.py up | 1..6 | down | list")
        return 2
    verb = args[0]
    backend = DockerBackend(port=DEFAULT_PORT)

    if verb == "up":
        backend.store_up(0)
        if os.path.exists(MEMO_PATH):
            os.remove(MEMO_PATH)
        print(f"store up on port {backend.port}; the memo is {MEMO_PATH}")
        return 0
    if verb == "down":
        backend.store_down(0)
        print("store down")
        return 0
    if verb == "list":
        for number in sorted(BEATS):
            spec = BEATS[number]
            print(f"{number}  {spec.title}  {spec.cases or spec.kind}")
        return 0

    try:
        number = int(verb)
    except ValueError:
        print("usage: dr_demo_beat.py up | 1..6 | down | list")
        return 2

    os.environ["FALKORDB_PORT"] = str(backend.port)
    try:
        spec = beat(number)
        print(f"== beat {number} — {spec.title} ==")
        if spec.kind == "guards":
            return _run_guards()
        client = _client()
        try:
            if spec.kind == "closer":
                _run_closer(client)
            else:
                for name in spec.cases:
                    _run_case(client, name, SCREENS_DIR)
        finally:
            client.close()
    except BeatError as exc:
        print(f"BEAT REFUSED: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
