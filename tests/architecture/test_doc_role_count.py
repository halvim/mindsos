"""The L2 role-set is closed; a doc that publishes a different size is wrong.

⚠ **WRITTEN BECAUSE FOUR NUMBERS FOR ONE CLOSED SET WERE IN CIRCULATION.**
Measured 2026-09-13: `docs/concepts/role-graphs.md` said 15,
`docs/api/knowledge/identifiers.md` said "15 (3 seed + 12 upper)",
`docs/dev/repo-layout.md` said 15 in three places, and `CLAUDE.md` carried a
growth chain that stopped at 16 — while `ALL_ROLES` had been 17 since the
policy role shipped. Five tests already assert `len(ALL_ROLES) == 18`; nothing
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

⚠ **THE PHRASE LIST IS A FLOOR, NOT A CEILING — and it has been measured to be
one.** Verification batch 2 (PR #231) found `internals/knowledge.md` giving the
size as "closed role-set is now 14", a phrasing this list did not have, so the
guard stayed green on a false count. A census of the live tree for that ship
(2026-09-21) found two more misses, both false: `concepts/knowledge-lifecycle.md`
"closed at **15 named entries**" and `concepts/user-local-authoring.md` "all 9
L2 role-graph schemas". All three phrasings are now listed, and
`test_every_phrasing_is_caught_on_a_fabricated_line` pins each pattern on a
fabricated line, so a phrasing with no live site today is still proven to fire.
A new phrasing found by reading goes into `_CLAIMS` AND into that test.
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
    re.compile(r"closed role-set is now \**(\d+)\b"),
    re.compile(r"closed at \*\*(\d+) named entries\b"),
    re.compile(r"\ball (\d+) L2 role-graph schemas\b"),
)


def _claimed_counts(line):
    """Every closed-set size ``line`` publishes, by the phrasings in ``_CLAIMS``."""
    if "categor" in line.lower():
        return []
    return [int(m.group(1)) for pattern in _CLAIMS for m in pattern.finditer(line)]


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
            for n in _claimed_counts(line):
                if n != expected:
                    offenders.add(
                        "%s:%d claims %d, ALL_ROLES is %d"
                        % (os.path.relpath(path, _ROOT), lineno, n, expected)
                    )
    assert not offenders, (
        "these pages publish a role-set size the code does not have:\n  "
        + "\n  ".join(sorted(offenders))
    )


#: (fabricated line, the size it must be read as). One row per ``_CLAIMS``
#: pattern, so each pattern is proven to fire even with no live site today.
_FABRICATED = (
    ("There are **99 named role-graphs** here.", 99),
    ("The set is closed at **99 named roles** per ADR-0150.", 99),
    ("s = schema_for_role(x)  # one of the 99 named roles", 99),
    ("It ships 99 role-schema builders.", 99),
    ("identifiers.py exports 99 role constants.", 99),
    ("There are 99 role-graph schema builders.", 99),
    ("closed set = **99 named** roles", 99),
    ("The closed role-set is now **99** roles.", 99),
    ("L2's role-set is closed at **99 named entries + 1 template**", 99),
    ("all 99 L2 role-graph schemas ship at strict=False", 99),
)

#: True lines about a SUBSET or another set — must never be read as a claim.
_NOT_CLAIMS = (
    "kl = KnowledgeLayer.bootstrap()  # fresh Global with 6 named roles, empty",
    "# mg has all 6 named roles ensured; 3 populated by importers.",
    "KnowledgeLayer with Global containing 6 named role-graphs;",
    "The 13 functional categories are closed at **13 named roles**.",
)


def test_every_phrasing_is_caught_on_a_fabricated_line():
    assert len(_FABRICATED) == len(_CLAIMS), "one fabricated row per pattern"
    for line, size in _FABRICATED:
        assert _claimed_counts(line) == [size], line


def test_subset_and_category_lines_are_not_claims():
    for line in _NOT_CLAIMS:
        assert _claimed_counts(line) == [], line
