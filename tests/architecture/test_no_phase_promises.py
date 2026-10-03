"""No live page promises that work arrives in a numbered phase.

Doc-fix mechanism: the forward-promise frame. Verification batches 3-6
(PRs #235, #240, #241, #243, #244) each found the same shape -- not a wrong
command, but a sentence about what ships NEXT: "the metagraph_loader lands in
Phase 08", "Future Phase 09 ships proper XRef migration", "in Phase 05c
MetaEdgeType will join it", "read-path soft-delete filter lands in Phase 10".
Every one had already shipped.

WHY IT IS DECIDABLE: the numbered-phase rollout ENDED at Phase 50 (the
`confirmation_docs/PHASE_NN_CONFIRMED.md` set is closed, and RULES says core
work now runs on `feat/*` branches with `<name>-confirmed` tags). So a live
page saying work *will* land in a numbered phase is either false, or a record
written in the present tense -- and in both cases the reader cannot tell which.

THE RULE: in a live or index doc (`tools/claim_inventory.partition` -- the one
definition of "live"), a line that promises a numbered phase must also say how
it turned out: shipped / landed / never built / retired. Past tense escapes on
its own ("landed at Phase 08" is not a promise). A promise in a dated record
(ADRs, the changelog, confirmation docs) is outside the domain, because a
record is allowed to say what was true on its date.

FLOOR, NOT CEILING: the phrasing list is what the four batches actually found,
plus the bare "a later phase". A promise written some other way is MISSED here
rather than reported wrong -- the same choice as `test_doc_role_count`. When a
batch finds a new phrasing, it goes in `_PROMISE` AND in `_FABRICATED` below.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_TOOL = _ROOT / "tools" / "claim_inventory.py"
_DOMAIN = frozenset({"live", "index"})

#: "<verb> in|to Phase NN" / "a later phase", present or future tense only.
_TARGET = r"(?:a later phase|Phase\s+\d+[a-z]*\+?)"
#: Verbs whose present tense reads as "still coming". `ship` is NOT here for the
#: bare and `at` forms: "what ships at Phase 28" legitimately records what that
#: phase delivered, and nothing in the line distinguishes it from a promise.
_ARRIVE = r"(?:lands?|land|arrives?|arrive|joins?|join|comes?|come)"
_PROMISE = re.compile(
    r"\b(?:will\s+)?(?:lands?|land|arrives?|arrive|joins?|join|comes?|come|ships?|ship|"
    r"deferred)\b[^.]{0,24}?\b(?:in|to)\s+" + _TARGET
    + r"|\bFuture\s+Phase\s+\d+"
    + r"|\bPhase\s+\d+[a-z]*\+?\s+will\s+(?:ship|land|add|bring|join)\b"
    # "<arrive-verb> [at|with] Phase NN" -- the preposition is optional, which is
    # how "lands Phase 47" and "lands at Phase 48" slipped past the first cut.
    + r"|\b(?:will\s+)?" + _ARRIVE + r"\b[^.]{0,24}?\b(?:at|with)?\s*Phase\s+\d+[a-z]*\+?"
    # "deferred at|to Phase NN" -- a deferral with no stated outcome.
    + r"|\bdeferred\b[^.]{0,30}?\b(?:at|to)\s+(?:the\s+first\s+consumer\s+\()?Phase\s+\d+",
)
#: The line says how it turned out, so it is a record, not a promise. The
#: outcome must be ON THE SAME LINE: the unit of judgement is the line, so a
#: promise whose resolution wraps onto the next one is reported, and the fix is
#: to put the outcome where the claim is.
_RESOLVED = re.compile(
    r"\b(shipped|landed|never built|not built|was never|retired|no longer"
    r"|exists? yet|does not exist|do not exist|never shipped|still open)\b",
    re.IGNORECASE,
)


def _load():
    spec = importlib.util.spec_from_file_location("claim_inventory_phase", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


inv = _load()


def _judged(root: Path):
    """Every line the guard JUDGES: (file, line number, text) of each live or
    index line carrying a phase promise. The one walk both callers share, so what is
    reported as adjudicated and what can be reported as a problem cannot
    drift apart."""
    tree = inv.load_tree(root)
    for rel in tree.files:
        if not rel.endswith(".md") or inv.partition(rel) not in _DOMAIN:
            continue
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            if _PROMISE.search(line):
                yield rel, n, line


def find_problems(root: Path) -> list[str]:
    return [
        f"{rel}:{n}: {line.strip()[:120]}"
        for rel, n, line in _judged(root)
        if not _RESOLVED.search(line)
    ]


def adjudicated_sites(root: Path) -> list[tuple[str, int]]:
    """Report mode (`tools/claim_inventory.py`, the emit contract): the
    `file:line` sites this guard adjudicated -- the lines carrying a phase promise,
    whichever way the judgement went. Every other live line was scanned, not
    judged, and is NOT emitted: this guard says nothing about it."""
    return [(rel, n) for rel, n, _ in _judged(root)]


def test_the_premise_holds_so_the_guard_cannot_pass_vacuously():
    assert (_ROOT / "docs").is_dir(), "docs/ missing - the image did not copy it"
    tree = inv.load_tree(_ROOT)
    assert any(inv.partition(f) == "live" for f in tree.files), "no live pages found"


def test_the_numbered_rollout_is_closed_so_a_promise_cannot_come_true():
    """The guard's premise, asserted rather than believed: the phase set is closed."""
    confirmed = sorted(
        int(p.name.split("_")[1])
        for p in (_ROOT / "confirmation_docs").glob("PHASE_[0-9][0-9]_CONFIRMED.md")
    )
    assert confirmed, "no PHASE_NN_CONFIRMED.md found - premise unmeasurable"
    assert max(confirmed) >= 50, (
        f"highest confirmed phase is {max(confirmed)}; if the rollout is running "
        "again, a forward promise can be true and this guard is wrong"
    )


def test_no_live_page_promises_a_numbered_phase():
    bad = find_problems(_ROOT)
    assert not bad, (
        f"{len(bad)} live line(s) promise a numbered phase without saying how it "
        "turned out (shipped / landed / never built / retired):\n" + "\n".join(bad)
    )


# -- fabricated corners ----------------------------------------------------

def _tree(root: Path, live: str, record: str = "This lands in Phase 09.\n") -> Path:
    (root / "docs" / "usage").mkdir(parents=True)
    (root / "docs" / "usage" / "p.md").write_text(live)
    (root / "docs" / "changelog").mkdir()
    (root / "docs" / "changelog" / "old.md").write_text(record)
    (root / "confirmation_docs").mkdir()
    (root / "confirmation_docs" / "PHASE_50_CONFIRMED.md").write_text("x\n")
    return root


#: one row per phrasing in `_PROMISE`, so each is proven to fire
_FABRICATED = (
    "The loader lands in Phase 08.",
    "IntergraphHyperEdge arrives in Phase 05c.",
    "MetaEdgeType joins it in Phase 05d.",
    "The parity test ships in Phase 27.",
    "Field-level parsing is deferred to Phase 28.",
    "Per-role tracking is deferred to a later phase.",
    "Phase 07 will ship the array form.",
    "Future Phase 09 ships proper XRef migration.",
    "The metagraph sync CLI lands Phase 08.",
    "The retention mechanism lands at Phase 48.",
    "Those schema types land with Phase 05.",
    "That arrives at Phase 31 alongside the CLI verb.",
    "The composite is deferred at Phase 36.",
)


def test_every_phrasing_is_caught_on_a_fabricated_line(tmp_path):
    for i, line in enumerate(_FABRICATED):
        root = tmp_path / f"c{i}"
        root.mkdir()
        assert len(find_problems(_tree(root, line + "\n"))) == 1, line


def test_a_resolved_line_is_true(tmp_path):
    page = (
        "The loader landed at Phase 08.\n"
        "Deferred to Phase 28, and never built.\n"
        "The tracking is deferred to a later phase - it was never built.\n"
        "The rule shipped at Phase 10.\n"
        "The composite is deferred at Phase 36 - no writing capacity exists yet.\n"
        "The retention mechanism lands at Phase 48; it never shipped.\n"
        "The sync CLI lands Phase 08 - that path does not exist.\n"
    )
    assert find_problems(_tree(tmp_path, page)) == []


def test_a_dated_record_is_outside_the_domain(tmp_path):
    assert find_problems(_tree(tmp_path, "nothing here\n")) == []


# -- report mode -----------------------------------------------------------

def test_it_emits_the_judged_lines_and_only_those(tmp_path):
    page = "The loader lands in Phase 08.\nA plain line.\nThe loader lands in Phase 08; it shipped.\n"
    assert adjudicated_sites(_tree(tmp_path, page)) == [("docs/usage/p.md", 1), ("docs/usage/p.md", 3)]


def test_every_reported_problem_is_an_emitted_site(tmp_path):
    root = _tree(tmp_path, "The loader lands in Phase 08.\nIt lands in Phase 09; shipped.\nnothing\n")
    emitted = {f"{f}:{n}" for f, n in adjudicated_sites(root)}
    problems = {p.split(": ", 1)[0] for p in find_problems(root)}
    assert problems == {"docs/usage/p.md:1"} and problems <= emitted
