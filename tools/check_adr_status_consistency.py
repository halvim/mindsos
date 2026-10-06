#!/usr/bin/env python3
"""ADR status-consistency checker (2026-07 doc-vs-code audit).

An ADR's status is currently duplicated in four places:

1. the ADR file's front-matter ``status:`` field,
2. the ADR file's prose ``**Status:**`` line,
3. the ADR index ``docs/decisions/adr/README.md`` (a "Status" column),
4. the per-layer summary tables ``docs/decisions/summary/*.md``
   (those with a "Status" column).

They drift. This checker is the guard: it asserts all four agree for
every ADR and exits non-zero on any mismatch, so ``mkdocs`` / the ship
gate can run it and fail loud instead of letting the index rot again.

It does NOT rewrite anything — it only reports. Run:

    python3 tools/check_adr_status_consistency.py

Compatibility rules (a status *cell* may be annotated, not bare):
  * ``Superseded by [ADR-XXXX](...)``  -> status ``superseded``
  * ``Amended by [ADR-XXXX](...)``     -> base status unchanged (an
    amendment does not flip Accepted->something); the cell is accepted
    as compatible with whatever the front-matter says.
  * bare ``Accepted`` / ``Proposed`` / ``Deferred`` / ``Withdrawn``
    -> must equal the front-matter status.

2026-08-01 repair (CORE-C1R4 follow-on). Three defects, all of which
made the guard report green while the index was stale:

  * **The index was never checked at all.** ``_iter_table_rows`` only
    armed itself when the table header contained a cell with "adr" in
    it. ``README.md``'s header is ``| # | Title | Status | Layer |
    Aliases |`` — no such cell — so zero rows were ever yielded and
    ``check_index`` was a no-op on the one file it exists to police.
    The index had silently stopped at ADR-0137, missing 76 rows.
  * **No completeness check.** An ADR absent from the index was
    invisible; only *disagreeing* rows could ever be reported. That is
    the defect that let the index rot in the first place, so the fix
    for it (``require_complete``) is the part that stops recurrence.
  * **Duplicate ADR numbers collapsed.** Statuses were keyed by
    ``filename[:4]``, so ``0172`` (2 files) and ``0201`` (4 files)
    shared one key each and the losers were silently discarded. Keyed
    by filename now; the index links carry the filename, so rows for
    amendment files are matched exactly.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ADR_DIR = Path(__file__).resolve().parent.parent / "docs" / "decisions" / "adr"
SUMMARY_DIR = ADR_DIR.parent / "summary"
README = ADR_DIR / "README.md"

CANON = {"accepted", "proposed", "superseded", "deferred", "withdrawn"}
#: Pull the ADR filename out of a markdown link target, with or without
#: a ``../adr/`` prefix (the summary pages use one, the README does not).
_ADR_HREF = re.compile(r"\]\((?:\.\./adr/|adr/)?([0-9]{4}[-A-Za-z0-9]*\.md)\)")

#: The two decision pages that claim a status for the ADRs they list, which
#: nothing checked until 2026-09-21: ``proposed.md`` said its entries were
#: "not yet scheduled" while most had shipped, and ``superseded.md``'s
#: "in flight" table called two long-superseded ADRs Accepted. Their links
#: are ``adr/NNNN-*.md`` (relative to ``docs/decisions/``), a form
#: ``_ADR_HREF`` did not accept, so ``check_index`` saw zero rows there.
DECISIONS_DIR = ADR_DIR.parent
PROPOSED_PAGE = DECISIONS_DIR / "proposed.md"
SUPERSEDED_PAGE = DECISIONS_DIR / "superseded.md"
INDEX_PAGES = (PROPOSED_PAGE, SUPERSEDED_PAGE)
_OPEN = {"proposed", "deferred"}
_BARE_NUMBER_CELL = re.compile(r"^([0-9]{4})$")


def _canon(text: str) -> str | None:
    """First canonical status keyword found in *text*, lowercased."""
    for w in re.findall(r"[A-Za-z]+", text or ""):
        if w.lower() in CANON:
            return w.lower()
    return None


_FM_STATUS = re.compile(r"^status:\s*(\w+)", re.MULTILINE)
_PROSE_STATUS = re.compile(r"^[-*\s]*\*\*Status:\*\*\s*(.+)$", re.MULTILINE)


def _frontmatter_status(md: str) -> str | None:
    m = _FM_STATUS.search(md)
    return m.group(1).lower() if m else None


def _prose_status(md: str) -> str | None:
    # Later ADRs use ``**Status:** X``; the earliest (0001-0013) use a
    # bullet ``- **Status:** X``. Accept either. Only the FIRST such
    # line counts — an in-file amendment section must therefore label
    # its own status differently (``**Amendment status:**``) so it does
    # not shadow the base ADR's.
    m = _PROSE_STATUS.search(md)
    return _canon(m.group(1)) if m else None


def _status_line_numbers(md: str) -> list[int]:
    """The 1-based lines an ADR file states its status on: the front-matter
    line and the first prose ``**Status:**`` line, whichever exist. These are
    the two lines :func:`load_adr_statuses` reads and compares."""
    out: list[int] = []
    m = _FM_STATUS.search(md)
    if m:
        out.append(md.count("\n", 0, m.start()) + 1)
    m = _PROSE_STATUS.search(md)
    if m:
        out.append(md.count("\n", 0, md.index("**Status:**", m.start())) + 1)
    return out


def load_adr_statuses(adr_dir: Path | None = None) -> tuple[dict[str, str], list[str]]:
    """Map ADR *filename* -> canonical status.

    ``adr_dir`` defaults to this checkout's ADR folder. A guard's report mode
    passes the folder of the tree it was asked to report on.

    Keyed by filename, not by the 4-digit number: ADR-0172 and ADR-0201
    each have amendment files sharing their number, and keying by number
    silently dropped all but one.
    """
    out: dict[str, str] = {}
    problems: list[str] = []
    for f in sorted((adr_dir or ADR_DIR).glob("[0-9][0-9][0-9][0-9]-*.md")):
        md = f.read_text(encoding="utf-8")
        fm = _frontmatter_status(md)          # YAML front-matter (may be None)
        pr = _prose_status(md)                # prose/bullet Status line
        # Authoritative = front-matter if present, else the prose line
        # (the early bullet-format ADRs carry no YAML status).
        authoritative = fm if fm is not None else pr
        if authoritative is None:
            problems.append(f"{f.name}: no status found (front-matter or prose)")
            continue
        if fm is not None and pr is not None and pr != fm:
            problems.append(
                f"{f.name}: front-matter '{fm}' != prose Status '{pr}'"
            )
        out[f.name] = authoritative
    for p in problems:
        print(f"  [ADR file]   {p}")
    return out, problems


def _iter_table_rows_n(md: str):
    """Yield ``(line number, status_cell, adr_filename)`` for every
    markdown-table row that lives under a header containing a 'Status' column
    and links an ADR file.

    A table is in scope iff its header row has a cell that is exactly
    ``status``. The previous version additionally required a cell
    containing "adr", which no shipped table has — so no row was ever
    yielded. See the module docstring.
    """
    for n, first, status in _status_table_rows_n(md):
        m = _ADR_HREF.search(first)
        if not m:
            continue
        yield n, status, m.group(1)


def _iter_table_rows(md: str):
    """``(status_cell, adr_filename)`` — :func:`_iter_table_rows_n` without
    the line number."""
    for _, status, fname in _iter_table_rows_n(md):
        yield status, fname


def _status_table_rows_n(md: str):
    """Yield ``(line number, first_cell, status_cell)`` for every data row of
    a table whose header has a cell that is exactly ``status``."""
    status_col = None
    for n, line in enumerate(md.splitlines(), 1):
        if not line.lstrip().startswith("|"):
            status_col = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        lowered = [c.lower() for c in cells]
        if "status" in lowered:
            status_col = lowered.index("status")
            continue
        if status_col is None or len(cells) <= status_col:
            continue
        if set(cells[0]) <= {"-", ":", " "}:  # separator row
            continue
        yield n, cells[0], cells[status_col]


def _status_table_rows(md: str):
    """``(first_cell, status_cell)`` — :func:`_status_table_rows_n` without
    the line number."""
    for _, first, status in _status_table_rows_n(md):
        yield first, status


def _judge_rows(md: str, name: str, adr_status: dict[str, str], seen: set[str]):
    """Yield ``(line number, problem or None)`` for every linked status row —
    the one walk :func:`check_index` and :func:`adjudicated_sites` share, so
    what is reported as adjudicated and what can be reported as a problem
    cannot drift apart. ``seen`` collects the ADR files that have a row."""
    for n, cell, fname in _iter_table_rows_n(md):
        truth = adr_status.get(fname)
        if truth is None:
            yield n, f"{name}: row links '{fname}', which is not an ADR file"
            continue
        seen.add(fname)
        low = cell.lower()
        if "amended by" in low:
            yield n, None  # amendment does not change base status
            continue
        cell_status = _canon(cell)
        if cell_status is None:
            yield n, None  # non-status annotation
            continue
        if cell_status != truth:
            yield n, (
                f"{name}: ADR {fname} cell '{cell}' != file status "
                f"'{truth}'"
            )
        else:
            yield n, None


def check_index(
    path: Path,
    adr_status: dict[str, str],
    *,
    require_complete: bool = False,
) -> list[str]:
    """Compare an index/summary table against the ADR files.

    ``require_complete`` additionally asserts that every ADR file has a
    row. Only the README claims to be a full index; the per-layer
    summaries are deliberately partial, so they are checked for
    agreement but not for coverage.
    """
    md = path.read_text(encoding="utf-8")
    seen: set[str] = set()
    problems = [p for _, p in _judge_rows(md, path.name, adr_status, seen) if p]
    if require_complete:
        for fname in sorted(set(adr_status) - seen):
            problems.append(
                f"{path.name}: ADR {fname} has no row in the index "
                f"(every ADR file must be listed)"
            )
    return problems


def _statuses_by_number(adr_status: dict[str, str]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for fname, status in adr_status.items():
        out.setdefault(fname[:4], set()).add(status)
    return out


def _judge_page(
    md: str,
    name: str,
    adr_status: dict[str, str],
    *,
    headings_claim_open: bool = False,
    superseded_section: str | None = None,
):
    """Yield ``(line number, problem or None)`` for claims 2-4 of
    :func:`check_index_page` — the one walk it and :func:`adjudicated_sites`
    share. A heading that names no ADR number, and a row with no link in a
    superseded section, are scanned and never judged."""
    by_number = _statuses_by_number(adr_status)

    for n, first, status in _status_table_rows_n(md):
        m = _BARE_NUMBER_CELL.match(first)
        if m:
            if _canon(status) is not None:
                yield n, (
                    f"{name}: row '{m.group(1)}' states status '{status}' "
                    "without linking the ADR file, so nothing checks it"
                )
            else:
                yield n, None

    section = ""
    for n, line in enumerate(md.splitlines(), 1):
        if line.startswith("## "):
            section = line[3:]
        if headings_claim_open and line.startswith("#") and "ADR" in line:
            nums = re.findall(r"\b([0-9]{4})\b", line)
            if "resolved" in section.lower() or "resolved" in line.lower():
                if nums:
                    yield n, None
                continue
            for num in nums:
                truth = by_number.get(num)
                if truth is None:
                    yield n, f"{name}: heading names ADR-{num}, which is not an ADR file"
                elif not truth & _OPEN:
                    yield n, (
                        f"{name}: heading presents ADR-{num} as open but it is "
                        f"{'/'.join(sorted(truth))}: {line.strip()}"
                    )
                else:
                    yield n, None
        if superseded_section and section.startswith(superseded_section):
            if line.startswith("|"):
                m = _ADR_HREF.search(line.split("|")[1] if line.count("|") > 1 else "")
                if m:
                    if adr_status.get(m.group(1)) != "superseded":
                        yield n, (
                            f"{name}: '{superseded_section}' lists {m.group(1)}, "
                            f"which is {adr_status.get(m.group(1))}"
                        )
                    else:
                        yield n, None


def check_index_page(
    path: Path,
    adr_status: dict[str, str],
    *,
    headings_claim_open: bool = False,
    superseded_section: str | None = None,
) -> list[str]:
    """Every status an index page states must be the ADR file's status.

    Four claims, each checked against ``load_adr_statuses`` (never typed):

    1. a Status-column cell on a linked row — ``check_index``;
    2. a Status-column row that names a bare number without linking the
       file makes a status claim nothing can check — reported, unless its
       status cell carries no status word (e.g. "number not in use");
    3. ``headings_claim_open``: a heading that names an ADR presents it as
       open, so the ADR must be Proposed or Deferred — except under a
       ``##`` section whose title says "Resolved", or a heading that itself
       says "Resolved";
    4. ``superseded_section``: every linked row under the ``##`` section
       with that title must be Superseded.
    """
    md = path.read_text(encoding="utf-8")
    problems = check_index(path, adr_status)
    problems += [
        p
        for _, p in _judge_page(
            md,
            path.name,
            adr_status,
            headings_claim_open=headings_claim_open,
            superseded_section=superseded_section,
        )
        if p
    ]
    return problems


#: The two decision index pages and the claims each one's own text makes.
#: Read by :func:`check_index_pages` and by :func:`adjudicated_sites`, so the
#: checker and its report cannot disagree about which page claims what.
_PAGE_CLAIMS: tuple[tuple[str, dict], ...] = (
    ("proposed.md", {"headings_claim_open": True}),
    ("superseded.md", {"superseded_section": "Effective supersessions"}),
)


def check_index_pages(adr_status: dict[str, str]) -> list[str]:
    """``check_index_page`` over the two decision index pages, each with the
    claims its own text makes."""
    problems: list[str] = []
    for name, claims in _PAGE_CLAIMS:
        problems += check_index_page(DECISIONS_DIR / name, adr_status, **claims)
    return problems


def adjudicated_sites(root: Path) -> list[tuple[str, int]]:
    """Report mode (``tools/claim_inventory.py``, the emit contract): the
    ``(repo-relative file, line)`` sites this checker adjudicated under
    ``root``, whichever way each judgement went:

    * the status line(s) of every ADR file;
    * every linked status row of the README index and of each summary page;
    * on the two index pages, also every bare-number status row, every
      heading that names an ADR number, and every linked row of the
      effective-supersessions section.

    An ADR file with NO row in the README has no site: it is reported as a
    problem and emits nothing. Every other line was scanned, not judged."""
    decisions = root / "docs" / "decisions"
    adr_dir = decisions / "adr"
    adr_status, _ = load_adr_statuses(adr_dir)
    out: set[tuple[str, int]] = set()
    for f in sorted(adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")):
        rel = f.relative_to(root).as_posix()
        out.update((rel, n) for n in _status_line_numbers(f.read_text(encoding="utf-8")))
    pages: list[tuple[Path, dict | None]] = [(adr_dir / "README.md", None)]
    pages += [(p, None) for p in sorted((decisions / "summary").glob("*.md"))]
    pages += [(decisions / name, claims) for name, claims in _PAGE_CLAIMS]
    for path, claims in pages:
        if not path.is_file():
            continue
        md = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        out.update((rel, n) for n, _ in _judge_rows(md, path.name, adr_status, set()))
        if claims is not None:
            out.update((rel, n) for n, _ in _judge_page(md, path.name, adr_status, **claims))
    return sorted(out)


def main() -> int:
    print("ADR status-consistency check")
    adr_status, adr_problems = load_adr_statuses()
    all_problems = list(adr_problems)

    if README.exists():
        for p in check_index(README, adr_status, require_complete=True):
            print(f"  [index]      {p}")
            all_problems.append(p)
    else:
        all_problems.append("README.md missing — the ADR index is the guard's subject")
        print("  [index]      README.md missing")

    for path in sorted(SUMMARY_DIR.glob("*.md")):
        for p in check_index(path, adr_status):
            print(f"  [summary]    {p}")
            all_problems.append(p)

    for p in check_index_pages(adr_status):
        print(f"  [page]       {p}")
        all_problems.append(p)

    n = len(adr_status)
    from collections import Counter
    dist = Counter(adr_status.values())
    print(
        f"\n{n} ADRs checked "
        f"({', '.join(f'{k}={v}' for k, v in sorted(dist.items()))})."
    )
    if all_problems:
        print(f"FAIL: {len(all_problems)} inconsistenc(ies).")
        return 1
    print("OK: all ADR statuses consistent across file, README, summaries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
