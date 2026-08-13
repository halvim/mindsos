"""Guard — the set of tracked ``*COORDINATION*.md`` files is closed at two.

RULES §5: a **live** cross-lane coordination file is transient, local-only,
gitignored, and lives in the shared checkout — never in git. Two tracked ones
are **closed history** and stay exactly where they are, because six committed
confirmation docs cite them by name and deleting them would break those
citations (critic ruling, 2026-08-13: narrow the rule, do not delete history).

``.gitignore`` carries ``*COORDINATION*.md``, but gitignore cannot untrack what
is already tracked — so without this test nothing stops a third tracked
coordination file from appearing and the closed set from becoming an exception
that grows, which is the decay shape RULES §10.3 names. This is
`rules-coordination-file-pin` (STATE.pending_designs), the guard that narrowing
owed.

**Where this runs.** The test image bakes ``confirmation_docs`` via ``COPY``
(both Dockerfile stages), and the Linux gate builds from a git-clean checkout,
so what this glob sees there IS the tracked set. The pre-filter must tar the
**lane worktree** (or use ``git archive``): tarring the *shared* checkout would
sweep in the live untracked coordination file and redden this guard falsely —
that red means "your tarball is not the tracked tree", not "the set grew".

Shown red by mutation: drop a third ``*COORDINATION*.md`` into
``confirmation_docs`` and this fails naming it.
"""

from __future__ import annotations

from pathlib import Path

#: The closed set. RULES §5 names these two as frozen history; this constant is
#: the machine-readable copy of that sentence. Growing this tuple requires
#: amending RULES §5 in the same commit — the guard exists to make that growth
#: a decision rather than a drift.
CLOSED_SET = (
    "ARC_PACKAGING_RUNTIME_COORDINATION.md",
    "COLLECTION_MAP_FANOUT_COORDINATION.md",
)


def _confirmation_docs() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "confirmation_docs"
        if candidate.is_dir():
            return candidate
    raise RuntimeError(
        "confirmation_docs/ not found above this test — the test image COPYs "
        "it (both Dockerfile stages); a layout without it cannot check RULES §5"
    )


def test_tracked_coordination_files_are_exactly_the_closed_set():
    found = sorted(p.name for p in _confirmation_docs().glob("*COORDINATION*.md"))
    assert found == sorted(CLOSED_SET), (
        f"the RULES §5 closed set of coordination files changed: {found!r}. A "
        "live coordination file must stay untracked in the shared checkout "
        "(and out of any test tarball); if this is a deliberate freeze of "
        "closed history, amend RULES §5 and CLOSED_SET in the same commit"
    )


def test_the_closed_set_files_actually_exist():
    """The guard must fail in BOTH directions: a vanished member is a broken
    citation in six committed confirmation docs, not a cleanup."""
    docs = _confirmation_docs()
    missing = [name for name in CLOSED_SET if not (docs / name).is_file()]
    assert missing == [], f"closed-history coordination files missing: {missing!r}"
