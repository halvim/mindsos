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
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ADR_DIR = Path(__file__).resolve().parent.parent / "docs" / "decisions" / "adr"
SUMMARY_DIR = ADR_DIR.parent / "summary"
README = ADR_DIR / "README.md"

CANON = {"accepted", "proposed", "superseded", "deferred", "withdrawn"}
_ADR_LINK = re.compile(r"\[?(\d{4})\]?\((?:\.\./adr/)?\d{4}[-a-z0-9]*\.md\)")
_ADR_NUM = re.compile(r"\b(\d{4})\b")


def _canon(text: str) -> str | None:
    """First canonical status keyword found in *text*, lowercased."""
    for w in re.findall(r"[A-Za-z]+", text or ""):
        if w.lower() in CANON:
            return w.lower()
    return None


def _frontmatter_status(md: str) -> str | None:
    m = re.search(r"^status:\s*(\w+)", md, re.MULTILINE)
    return m.group(1).lower() if m else None


def _prose_status(md: str) -> str | None:
    # Later ADRs use ``**Status:** X``; the earliest (0001-0013) use a
    # bullet ``- **Status:** X``. Accept either.
    m = re.search(r"^[-*\s]*\*\*Status:\*\*\s*(.+)$", md, re.MULTILINE)
    return _canon(m.group(1)) if m else None


def load_adr_statuses() -> tuple[dict[str, str], list[str]]:
    out: dict[str, str] = {}
    problems: list[str] = []
    for f in sorted(ADR_DIR.glob("[0-9][0-9][0-9][0-9]-*.md")):
        num = f.name[:4]
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
        out[num] = authoritative
    for p in problems:
        print(f"  [ADR file]   {p}")
    return out, problems


def _iter_table_rows(md: str):
    """Yield (status_cell, adr_num) for every markdown-table row that
    lives under a header containing a 'Status' column."""
    status_col = None
    for line in md.splitlines():
        if not line.lstrip().startswith("|"):
            status_col = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # header row?
        lowered = [c.lower() for c in cells]
        if "status" in lowered and "adr #" in lowered or (
            "status" in lowered and any("adr" in c for c in lowered)
        ):
            status_col = lowered.index("status")
            continue
        if status_col is None or len(cells) <= status_col:
            continue
        if set(cells[0]) <= {"-", ":", " "}:  # separator row
            continue
        m = _ADR_NUM.search(cells[0])
        if not m:
            continue
        yield cells[status_col], m.group(1)


def check_index(path: Path, adr_status: dict[str, str]) -> list[str]:
    problems: list[str] = []
    md = path.read_text(encoding="utf-8")
    for cell, num in _iter_table_rows(md):
        truth = adr_status.get(num)
        if truth is None:
            continue  # ADR not in the canonical set (e.g. reserved number)
        low = cell.lower()
        if "amended by" in low:
            continue  # amendment does not change base status
        cell_status = _canon(cell)
        if cell_status is None:
            continue  # non-status annotation
        if cell_status != truth:
            problems.append(
                f"{path.name}: ADR {num} cell '{cell}' != file status "
                f"'{truth}'"
            )
    return problems


def main() -> int:
    print("ADR status-consistency check")
    adr_status, adr_problems = load_adr_statuses()
    all_problems = list(adr_problems)

    for path in [README, *sorted(SUMMARY_DIR.glob("*.md"))]:
        if path.exists():
            for p in check_index(path, adr_status):
                print(f"  [index]      {p}")
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
