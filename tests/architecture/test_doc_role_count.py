"""The L2 role-set is closed; a doc that publishes a different size is wrong.

⚠ **WRITTEN BECAUSE FOUR NUMBERS FOR ONE CLOSED SET WERE IN CIRCULATION.**
Measured 2026-09-13: `docs/concepts/role-graphs.md` said 15,
`docs/api/knowledge/identifiers.md` said "15 (3 seed + 12 upper)",
`docs/dev/repo-layout.md` said 15 in three places, and `CLAUDE.md` carried a
growth chain that stopped at 16 — while `ALL_ROLES` had been 17 since the
policy role shipped. Five tests already assert `len(ALL_ROLES) == 17`; nothing
asserted that the pages a reader opens agree with it.

⚠ **The number is DERIVED, never written here.** A guard with the count typed
into it is a second place to update, which is the defect it is meant to stop.

⚠ **SCOPE — `docs/` ONLY, and that is not an oversight.** The test image copies
`docs/` but does **not** copy `CLAUDE.md` or `README.md` (see the Dockerfile
test stage). A guard that scanned them would find no file, no claims, and go
green in the container for exactly the wrong reason. `CLAUDE.md` is corrected
by hand and is not covered here.

Excluded on purpose: `docs/decisions/adr/` and `docs/changelog/` record what was
true at a date, and `docs/_workbench/` is scratch. A guard that reddens on a
historical record is one that gets deleted.

⚠ **THE PATTERNS ARE EXACT PHRASES, NOT `N named roles`.** A generic pattern
matched three lines that count a *realm*, not the closed set — `global-local.md`
"fresh Global with 6 named roles" and "mg has all 6 named roles ensured", and
`usage/knowledge/overview.md` "Global containing 6 named role-graphs". All three
are true of a subset. A first cut reported them wrong, and a scope-word skip
(`global`/`local`/`bootstrap`) still missed the "mg has all 6" line, because the
distinguishing feature was never a keyword — it is the phrasing a canonical
claim uses.

⚠ Deliberately NARROW, like `test_dr_docs_guards.py`: a closed-set claim written
some other way is MISSED here rather than reported wrong. `category` lines are
the L3 set (`FUNCTIONAL_CATEGORIES`, 13) and are skipped outright.
"""

from __future__ import annotations

import io
import os
import re

from mindsos_knowledge.identifiers import ALL_ROLES

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DOCS = os.path.join(_ROOT, "docs")
_SKIP_DIRS = ("decisions", "changelog", "_workbench")

_CLAIMS = (
    re.compile(r"\*\*(\d+) named role-graphs\*\*"),
    re.compile(r"closed at \*\*(\d+) named roles\*\*"),
    re.compile(r"\bone of the (\d+) named roles\b"),
    re.compile(r"\b(\d+) role-schema builders\b"),
    re.compile(r"\b(\d+) role constants\b"),
    re.compile(r"\b(\d+) role-graph schema builders\b"),
    re.compile(r"closed set\s*=\s*\*\*(\d+) named\b"),
)


def _live_docs():
    for dirpath, dirnames, filenames in os.walk(_DOCS):
        rel = os.path.relpath(dirpath, _DOCS)
        top = rel.split(os.sep)[0]
        if top in _SKIP_DIRS:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and d != "__pycache__"]
        for name in filenames:
            if name.endswith(".md") and not name.startswith(".fuse_hidden"):
                yield os.path.join(dirpath, name)


def test_the_docs_tree_is_present_so_this_guard_can_fail():
    """Abort rather than pass vacuously if docs/ was not copied."""
    assert os.path.isdir(_DOCS), f"no docs tree at {_DOCS}"
    assert any(_live_docs()), "docs tree present but no live pages found"


def test_no_live_doc_publishes_a_role_count_that_is_not_the_code_s():
    expected = len(ALL_ROLES)
    offenders = set()
    for path in _live_docs():
        text = io.open(path, encoding="utf-8").read()
        for lineno, line in enumerate(text.splitlines(), 1):
            if "categor" in line.lower():
                continue
            for pattern in _CLAIMS:
                for m in pattern.finditer(line):
                    if int(m.group(1)) != expected:
                        offenders.add(
                            "%s:%d claims %s, ALL_ROLES is %d"
                            % (os.path.relpath(path, _ROOT), lineno, m.group(1), expected)
                        )
    assert not offenders, (
        "these pages publish a role-set size the code does not have:\n  "
        + "\n  ".join(sorted(offenders))
    )
