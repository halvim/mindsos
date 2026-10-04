"""An ADR may not advertise a phase as pending once that phase has shipped.

Doc-fix mechanism: status headers. `§Implementation` headings carry a status
label, and the convention is that the label is updated when the work lands --
shipped ADRs read `## §Implementation (Phase 28 -- 2026-05-24)`. Eighteen never
were: at `b9fc4cf`, ADRs 0163-0180 still read `(Phase 46|47|48 ...; pending
ship)` while `confirmation_docs/PHASE_46|47|48_CONFIRMED.md` have existed since
June. A reader takes those three phases for unbuilt design.

THE PREMISE IS THE REPO'S OWN: `confirmation_docs/PHASE_NN_CONFIRMED.md` is
what the release ceremony writes when phase NN ships, and `confirmation_docs`
IS COPYed into the test image. `STATE.json` is NOT copied and can never be a
guard's source of truth. Nothing here is typed: the shipped set is read off the
filenames.

WHAT THIS ASSERTS is only that the false present-tense claim is gone -- not
that any particular ADR's implementation landed. The honest replacement for a
heading cites the confirmation doc, which is the repo's own definition of a
phase having shipped.

FLOOR, NOT CEILING -- and the exclusions were measured, not assumed:

* Only `#` HEADING lines. Prose that pairs a confirmed phase with an unshipped
  claim is out of scope because every such line in the tree is an explicitly
  dated snapshot that was true when written -- ADR-0120's table column is
  literally headed "Status at P24", ADR-0073 says "NOT shipped at halvim Phase
  ...", ADR-0169 says "At Phase 46 ... not yet shipped", ADR-0118's is a dated
  substrate-gate list, ADR-0156 cites "per Phase 38 carry-forward #3". Two of
  them are still substantively true (`mindsos_knowledge/migration.py` and
  `FalkorDBLocalPersister` do not exist). REWRITING A DATED RECORD FALSIFIES
  IT -- doc-fix #1's rule. A heading is a label, not a record.
* Only ADRs whose status is `accepted`, read with the ADR status checker's own
  loader. A Proposed or Deferred ADR naming a phase is not claiming to have
  shipped in it.
* A heading with no parsable `Phase NN` cannot be judged and is left alone.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_ADR_REL = "docs/decisions/adr"
_ADR_DIR = _ROOT / _ADR_REL
_CONF_DIR = _ROOT / "confirmation_docs"
_CHECKER = _ROOT / "tools" / "check_adr_status_consistency.py"

PENDING = "pending ship"

_HEADING = re.compile(r"^#{1,6}\s")
_PHASES = re.compile(r"Phases?\s+(\d+)(?:\s*[-–]\s*(\d+))?")
_CONFIRMED = re.compile(r"^PHASE_(\d+)_CONFIRMED\.md$")
_IMPL_HEADING = re.compile(r"^#{1,6}\s.*§Implementation\s*\(Phase\s+\d+")


def _phases_named(line: str) -> set[int]:
    out: set[int] = set()
    for lo, hi in _PHASES.findall(line):
        lo_i = int(lo)
        out.update(range(lo_i, int(hi) + 1) if hi else [lo_i])
    return out


def _judged(adrs: dict[str, tuple[str, str]]):
    """Every line the guard JUDGES: (filename, line number, phases named) for
    each HEADING of an Accepted ADR that says 'pending ship' AND names a
    parsable phase. The one walk both callers share, so what is reported as
    adjudicated and what can be reported as a problem cannot drift apart. A
    heading with no parsable phase cannot be judged and is not yielded."""
    for name, (status, text) in sorted(adrs.items()):
        if status != "accepted":
            continue
        for n, line in enumerate(text.split("\n"), 1):
            if not _HEADING.match(line) or PENDING not in line:
                continue
            phases = _phases_named(line)
            if phases:
                yield name, n, phases


def find_problems(adrs: dict[str, tuple[str, str]], confirmed: set[int]) -> list[str]:
    """Pure predicate. ``adrs`` maps filename -> (canonical status, text)."""
    problems: list[str] = []
    for name, n, named in _judged(adrs):
        shipped = sorted(named & confirmed)
        if shipped:
            phases = ", ".join(str(p) for p in shipped)
            problems.append(
                f"{name}:{n} advertises Phase {phases} as '{PENDING}', "
                f"but confirmation_docs records {'it' if len(shipped) == 1 else 'them'} shipped"
            )
    return problems


def _load_checker():
    spec = importlib.util.spec_from_file_location("adr_status_checker_ps", _CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _confirmed_phases(root: Path = _ROOT) -> set[int]:
    conf = root / "confirmation_docs"
    if not conf.is_dir():
        return set()
    return {
        int(m.group(1))
        for p in conf.iterdir()
        if (m := _CONFIRMED.match(p.name)) and p.stat().st_size > 0
    }


def _real_inputs(root: Path = _ROOT):
    mod = _load_checker()
    adr_dir = root / _ADR_REL
    statuses, _ = mod.load_adr_statuses(adr_dir)
    adrs = {n: (s, (adr_dir / n).read_text(encoding="utf-8")) for n, s in statuses.items()}
    return adrs, _confirmed_phases(root)


def adjudicated_sites(root: Path) -> list[tuple[str, int]]:
    """Report mode (`tools/claim_inventory.py`, the emit contract): the
    `file:line` sites this guard adjudicated -- each 'pending ship' heading of
    an Accepted ADR that names a phase, whichever way the judgement went.

    EMPTY ON A CLEAN TREE WHERE NO SUCH HEADING IS LEFT, and that is the honest
    report: with none, the guard judged nothing. The corners below prove the
    emitter is alive. An ADR is a dated record, so these sites add nothing to
    any live page's coverage."""
    adrs, _ = _real_inputs(root)
    return [(f"{_ADR_REL}/{name}", n) for name, n, _ in _judged(adrs)]


def test_the_premise_holds_so_the_guard_cannot_pass_vacuously():
    assert _ADR_DIR.is_dir(), "docs/decisions/adr missing - the image did not copy docs/"
    assert _CONF_DIR.is_dir(), "confirmation_docs missing - the shipped set has no source"
    adrs, confirmed = _real_inputs()
    assert confirmed, "no PHASE_NN_CONFIRMED.md found - the shipped set is empty, so nothing can redden"
    accepted = {n: t for n, (s, t) in adrs.items() if s == "accepted"}
    assert accepted, "no Accepted ADRs loaded - the checker's loader or glob is wrong"
    labelled = [
        (n, ln)
        for n, t in accepted.items()
        for ln in t.split("\n")
        if _IMPL_HEADING.match(ln)
    ]
    assert labelled, "no ADR uses the '§Implementation (Phase NN' heading - the domain is wrong"
    updated = [ln for _, ln in labelled if PENDING not in ln]
    assert updated, (
        "every §Implementation heading still says 'pending ship' - the convention that the "
        "label is updated when a phase ships is not evidenced in the tree"
    )


def test_no_accepted_adr_calls_a_shipped_phase_pending():
    adrs, confirmed = _real_inputs()
    problems = find_problems(adrs, confirmed)
    assert not problems, f"{len(problems)} stale pending-ship label(s):\n" + "\n".join(problems)


_CONF = {46, 47, 48}
_HEAD = "## §Implementation (Phase {p}; " + PENDING + ")\n"


def _run(text: str, status: str = "accepted", confirmed=None):
    return find_problems({"0999-x.md": (status, text)}, set(_CONF if confirmed is None else confirmed))


def test_fabricated_adrs_exercise_every_corner():
    assert len(_run(_HEAD.format(p=47))) == 1
    assert "Phase 47" in _run(_HEAD.format(p=47))[0]
    assert _run(_HEAD.format(p=99)) == []
    assert _run(_HEAD.format(p=47), status="deferred") == []
    assert _run(_HEAD.format(p=47), status="proposed") == []
    assert _run("The work is " + PENDING + " at Phase 47, per the P24 snapshot.\n") == []
    assert _run("## §Implementation (" + PENDING + ")\n") == []
    assert _run("## §Implementation (Phase 46 — convergence; shipped)\n") == []
    ranged = _run("## §Implementation (Phases 46-48; " + PENDING + ")\n")
    assert len(ranged) == 1 and "Phase 46, 47, 48" in ranged[0]
    assert _run(_HEAD.format(p=47), confirmed=set()) == []


# -- report mode -----------------------------------------------------------

_PAGE = (
    "---\nstatus: {s}\n---\n# ADR\n"
    "## §Implementation (Phase 47; " + PENDING + ")\n"
    "## §Implementation (Phase 99; " + PENDING + ")\n"
    "## §Implementation (" + PENDING + ")\n"
    "The work is " + PENDING + " at Phase 47.\n"
    "## §Implementation (Phase 46 — shipped)\n"
)


def _tree(root: Path, status: str = "accepted") -> Path:
    (root / _ADR_REL).mkdir(parents=True)
    (root / _ADR_REL / "0999-x.md").write_text(_PAGE.format(s=status), encoding="utf-8")
    (root / "confirmation_docs").mkdir()
    (root / "confirmation_docs" / "PHASE_47_CONFIRMED.md").write_text("shipped\n", encoding="utf-8")
    return root


def test_it_emits_the_judged_headings_and_only_those(tmp_path):
    """Lines 5 and 6 are judged (one way each). Line 7 names no phase, line 8
    is prose, line 9 does not say pending: scanned, never judged."""
    assert adjudicated_sites(_tree(tmp_path)) == [(f"{_ADR_REL}/0999-x.md", 5), (f"{_ADR_REL}/0999-x.md", 6)]


def test_an_adr_that_is_not_accepted_emits_nothing(tmp_path):
    assert adjudicated_sites(_tree(tmp_path, status="deferred")) == []


def test_every_reported_problem_is_an_emitted_site(tmp_path):
    root = _tree(tmp_path)
    emitted = {f"{f}:{n}" for f, n in adjudicated_sites(root)}
    problems = {f"{_ADR_REL}/" + p.split(" ", 1)[0] for p in find_problems(*_real_inputs(root))}
    assert problems == {f"{_ADR_REL}/0999-x.md:5"} and problems <= emitted
