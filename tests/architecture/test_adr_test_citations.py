"""An Accepted ADR may not cite a test file that does not exist without saying so.

Doc-fix mechanism #4 (`_doc-audit` NEW-1). ADRs cite tests as the evidence that
a decision holds. At `201d686`, 40 citations in 22 ADRs named files that do not
resolve — and 28 of the 29 distinct paths never existed in this repo's history:
they were plan-time names, written before the tests were built under other
names. Nothing noticed, because `tools/check_adr_status_consistency.py` checks
status words and index rows and never resolves a path.

⚠ **THE CITATION IS A SYMPTOM; THE CLAIM IT CARRIED IS THE FINDING.** A dead
citation is not fixed by rewriting the path (that would invent a mapping the
author never made, and falsify a dated record) nor by noting "never created"
(that hides whether the decision is tested at all). Each Accepted ADR with a dead
citation carries an in-file amendment whose heading contains the exact phrase

    test citations not in this repo

and lists every dead path once, as a bullet, with exactly ONE disposition:

- ``covered by `<path>`[, `<path>`]`` — each pointer must resolve;
- ``retired: <why>`` — the behaviour itself was removed;
- ``untested — filed as `ATG-<n>``` — the id must be a row of
  ``docs/plans/ADR_TEST_GAPS.md``.

The original ADR text is left untouched.

Domain — what the test image COPIES: `docs/`, `tests/`, `tests_server/`,
`tools/`. ⚠ `scripts/` is NOT copied, so a `scripts/` citation is out of scope
(it would resolve in a checkout and fail in the container). Only ADRs whose
status is ``accepted`` — read with the ADR status checker's own loader, so an
amendment file without front-matter is not silently skipped. Proposed and
Deferred ADRs may legitimately name tests that do not exist yet.

⚠ **FLOOR, NOT CEILING.** Bare ``test_*.py`` names without a directory are NOT
checked: several are true prose about a test that does not exist (ADR-0181:40)
or a rename record (ADR-0199:104). A static guard also cannot see that a
``covered by`` target auto-skips; that is checked by reading, at sweep time.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_ADR_REL = "docs/decisions/adr"
_GAP_REL = "docs/plans/ADR_TEST_GAPS.md"
_ADR_DIR = _ROOT / _ADR_REL
_GAP_PLAN = _ROOT / _GAP_REL
_CHECKER = _ROOT / "tools" / "check_adr_status_consistency.py"
_RESOLVE_ROOTS = ("tests", "tests_server", "tools")

ACK_PHRASE = "test citations not in this repo"

_CITE = re.compile(r"(?<![\w/.])((?:tests_server|tests|tools)/[\w./-]*?\.py)")
_HEADING = re.compile(r"^(#{1,6})\s")
_BULLET = re.compile(r"^\s*[-*]\s+`((?:tests_server|tests|tools)/[\w./-]*?\.py)`(.*)$")
_COVERED = re.compile(r"\bcovered by\s+`")
_RETIRED = re.compile(r"\bretired:\s*\S")
_FILED = re.compile(r"\buntested\s+—\s+filed as\s+`(ATG-\d+)`")
_GAP_ROW = re.compile(r"^\|\s*(ATG-\d+)\s*\|", re.MULTILINE)


def _load_checker():
    spec = importlib.util.spec_from_file_location("adr_status_checker_4", _CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _existing_files(root: Path) -> set[str]:
    out: set[str] = set()
    for d in _RESOLVE_ROOTS:
        base = root / d
        if base.is_dir():
            out.update(p.relative_to(root).as_posix() for p in base.rglob("*.py"))
    return out


def _split_ack_section(text: str) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """(lines outside the acknowledgement section, lines inside it), 1-based."""
    outside: list[tuple[int, str]] = []
    inside: list[tuple[int, str]] = []
    level = None
    for n, line in enumerate(text.split("\n"), 1):
        m = _HEADING.match(line)
        if m:
            if ACK_PHRASE in line:
                level = len(m.group(1))
                continue
            if level is not None and len(m.group(1)) <= level:
                level = None
        (inside if level is not None else outside).append((n, line))
    return outside, inside


def _judged(adrs: dict[str, tuple[str, str]]):
    """Every line the guard JUDGES: (filename, line number, text, inside the
    acknowledgement?) for each line of an Accepted ADR that carries a test-path
    citation. Per ADR the acknowledgement's lines come first, because a
    citation outside it is judged against what the acknowledgement lists. The
    one walk both callers share, so what is reported as adjudicated and what
    can be reported as a problem cannot drift apart. A line with no citation
    is scanned, never judged."""
    for name, (status, text) in sorted(adrs.items()):
        if status != "accepted":
            continue
        outside, inside = _split_ack_section(text)
        for n, line in inside:
            if _CITE.search(line):
                yield name, n, line, True
        for n, line in outside:
            if _CITE.search(line):
                yield name, n, line, False


def find_problems(adrs: dict[str, tuple[str, str]], existing: set[str], gap_ids: set[str]) -> list[str]:
    """Pure predicate. ``adrs`` maps filename -> (canonical status, text)."""
    problems: list[str] = []
    listed_by: dict[str, dict[str, int]] = {}
    for name, n, line, inside in _judged(adrs):
        listed = listed_by.setdefault(name, {})
        if not inside:
            for p in _CITE.findall(line):
                if p not in existing and p not in listed:
                    problems.append(f"{name}:{n} cites `{p}`, which does not exist and is not acknowledged")
            continue
        b = _BULLET.match(line)
        if b:
            path, rest = b.group(1), b.group(2)
            listed[path] = n
            if path in existing:
                problems.append(f"{name}:{n} lists `{path}` as not in this repo, but it exists")
            kinds = sum(bool(p.search(rest)) for p in (_COVERED, _RETIRED, _FILED))
            if kinds != 1:
                problems.append(f"{name}:{n} `{path}` needs exactly one disposition, has {kinds}")
            for gid in _FILED.findall(rest):
                if gid not in gap_ids:
                    problems.append(f"{name}:{n} `{path}` filed as {gid}, not a row of {_GAP_PLAN.name}")
            pointers = _CITE.findall(rest)
            for p in pointers:
                if p not in existing:
                    problems.append(f"{name}:{n} `{path}` points at `{p}`, which does not exist")
            if _COVERED.search(rest) and not pointers:
                problems.append(f"{name}:{n} `{path}` is 'covered by' nothing")
        else:
            for p in _CITE.findall(line):
                if p not in existing:
                    problems.append(f"{name}:{n} `{p}` inside the acknowledgement is not a bullet")
    return problems


def _real_inputs(root: Path = _ROOT):
    mod = _load_checker()
    adr_dir = root / _ADR_REL
    statuses, _ = mod.load_adr_statuses(adr_dir)
    adrs = {n: (s, (adr_dir / n).read_text(encoding="utf-8")) for n, s in statuses.items()}
    gap_plan = root / _GAP_REL
    gap_ids = set(_GAP_ROW.findall(gap_plan.read_text(encoding="utf-8"))) if gap_plan.is_file() else set()
    return adrs, _existing_files(root), gap_ids


def adjudicated_sites(root: Path) -> list[tuple[str, int]]:
    """Report mode (`tools/claim_inventory.py`, the emit contract): the
    `file:line` sites this guard adjudicated -- each line of an Accepted ADR
    that carries a test-path citation, whichever way the judgement went (it
    resolves, it is acknowledged, or it is a problem). A line with no citation
    was scanned, not judged, and is NOT emitted. An ADR is a dated record, so
    these sites add nothing to any live page's coverage."""
    adrs, _, _ = _real_inputs(root)
    return sorted({(f"{_ADR_REL}/{name}", n) for name, n, _, _ in _judged(adrs)})


def test_the_premise_holds_so_the_guard_cannot_pass_vacuously():
    assert _ADR_DIR.is_dir(), "docs/decisions/adr missing — the image did not copy docs/"
    for d in ("tests", "tools"):
        assert (_ROOT / d).is_dir(), f"{d}/ missing — nothing to resolve citations against"
    adrs, existing, _ = _real_inputs()
    accepted = {n: t for n, (s, t) in adrs.items() if s == "accepted"}
    assert accepted, "no Accepted ADRs loaded — the checker's loader or glob is wrong"
    resolving = sum(p in existing for t in accepted.values() for p in _CITE.findall(t))
    assert resolving > 0, "no Accepted ADR citation resolves — the resolver is broken, not the ADRs"


def test_every_dead_test_citation_in_an_accepted_adr_is_acknowledged():
    adrs, existing, gap_ids = _real_inputs()
    problems = find_problems(adrs, existing, gap_ids)
    assert not problems, f"{len(problems)} ADR test-citation problem(s):\n" + "\n".join(problems)


_ADR = "---\nstatus: {s}\n---\n# ADR\n\nTests: `tests/gone/test_x.py` and `tests/live/test_y.py`.\n"
_ACK = "\n## Amendment — " + ACK_PHRASE + " (2026-09-15)\n\n- `tests/gone/test_x.py` — {d}\n"
_LIVE = {"tests/live/test_y.py", "tests/live/test_z.py"}


def _run(text: str, status: str = "accepted", gaps=frozenset({"ATG-1"})):
    return find_problems({"0999-x.md": (status, text)}, set(_LIVE), set(gaps))


def test_fabricated_adrs_exercise_every_corner():
    base = _ADR.format(s="accepted")
    assert len(_run(base)) == 1 and "not acknowledged" in _run(base)[0]
    assert _run(_ADR.format(s="deferred"), status="deferred") == []
    assert _run(base + _ACK.format(d="covered by `tests/live/test_z.py`.")) == []
    assert _run(base + _ACK.format(d="retired: the module was deleted.")) == []
    assert _run(base + _ACK.format(d="untested — filed as `ATG-1`.")) == []
    assert "not a row" in _run(base + _ACK.format(d="untested — filed as `ATG-7`."))[0]
    assert "does not exist" in _run(base + _ACK.format(d="covered by `tests/gone/test_w.py`."))[0]
    assert "exactly one disposition" in _run(base + _ACK.format(d="see elsewhere."))[0]
    assert "exactly one disposition" in _run(
        base + _ACK.format(d="retired: gone; covered by `tests/live/test_z.py`.")
    )[0]
    misspelt = base + _ACK.format(d="retired: gone.").replace(ACK_PHRASE, "test citation not in this repo")
    assert any("not acknowledged" in p for p in _run(misspelt))
    stale = _ADR.format(s="accepted") + "\n## Amendment — " + ACK_PHRASE + "\n\n- `tests/live/test_y.py` — retired: x.\n"
    assert any("but it exists" in p for p in _run(stale))


# -- report mode -----------------------------------------------------------

def _tree(root: Path, status: str = "accepted", ack: str = "") -> Path:
    (root / _ADR_REL).mkdir(parents=True)
    (root / _ADR_REL / "0999-x.md").write_text(_ADR.format(s=status) + "No citation here.\n" + ack, encoding="utf-8")
    (root / "tests" / "live").mkdir(parents=True)
    (root / "tests" / "live" / "test_y.py").write_text("", encoding="utf-8")
    (root / "tests" / "live" / "test_z.py").write_text("", encoding="utf-8")
    return root


def test_it_emits_the_citing_lines_and_only_those(tmp_path):
    """Line 6 cites (one dead path, one live). Line 7 cites nothing. Line 11
    is the acknowledgement's bullet. Headings and blank lines carry no
    citation: scanned, never judged."""
    root = _tree(tmp_path, ack=_ACK.format(d="covered by `tests/live/test_z.py`."))
    assert adjudicated_sites(root) == [(f"{_ADR_REL}/0999-x.md", 6), (f"{_ADR_REL}/0999-x.md", 11)]
    assert find_problems(*_real_inputs(root)) == []


def test_an_adr_that_is_not_accepted_emits_nothing(tmp_path):
    assert adjudicated_sites(_tree(tmp_path, status="deferred")) == []


def test_every_reported_problem_is_an_emitted_site(tmp_path):
    root = _tree(tmp_path)
    emitted = {f"{f}:{n}" for f, n in adjudicated_sites(root)}
    problems = {f"{_ADR_REL}/" + p.split(" ", 1)[0] for p in find_problems(*_real_inputs(root))}
    assert problems == {f"{_ADR_REL}/0999-x.md:6"} and problems <= emitted
