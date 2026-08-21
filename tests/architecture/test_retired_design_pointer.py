"""Guard — a live file naming a retired design must name the design that replaced it.

**The failure this exists to stop, in full.** On 2026-08-20 the Decision Records
lane asked how an input enters MindsOS and how the system decides what to do with
it. It searched the tree thoroughly and answered, with file:line evidence,
``process -> hint -> derive_goal -> map`` per ``mindsos_intelligence/phase_1.py``
and ADR-0172. That answer was **shipped, coherent, Accepted-by-ADR-0172 — and one
design generation out of date**: ADR-0206 §3 drops ``derive_goal`` and makes
planning a loop, §4 retires ``MAX_DEPTH``, §8 deletes the thirteen
``placeholder=True`` capacities. Nothing in the code or in the published concept
docs said so. Reading the tree carefully produced the wrong answer with full
confidence, and the lane acted on it.

The tree's own rule is that **a document about the tree is never evidence**
(``RULES.md`` §12). So the fix is not prose promising to keep the pointers
current; it is this test, which fails when a pointer is missing.

**Claim 1 — the retired-token pointer.** Every scanned file that names a token
ADR-0206 retires must also name ``ADR-0206``. The domain is **derived by scan at
test time**, never recalled: any file added tomorrow that mentions ``derive_goal``
inherits the obligation without anyone remembering to list it. What is recalled is
the *token set* — the union of the two axes ``RULES.md`` §12 requires, since
neither closes alone (a derived domain cannot know which vocabulary is retired,
and a recalled file list cannot see new files).

**Claim 2 — item pointers resolve.** Every ``CORE-C4Rn`` cited in the scanned
domain must exist in ``CORE_RECONCILIATION_PLAN.md`` §5. Found by the same 2026-08
read-through: ``CORE-C4R9`` was cited in four modules and **has never existed** —
§5 declares C4R1 through C4R8. A reader who did follow the pointer landed nowhere.
A pointer that does not resolve is the same defect as a pointer that is missing.

**What this guard cannot do.** It cannot notice that a *new* design has superseded
an old one — that judgement is a human act, and ``RULES.md`` §9 is where it is
recorded (status flip, or an amendment carrying ``Proposed``). This guard enforces
the consequence, not the judgement: once the pair is declared here, the tree cannot
drift back. Extending it to a new pair is one row in :data:`RETIRED`.

Three guards were costed for this ship and two were refused, on measurement:

* *"every Accepted ADR revised by a Proposed one carries a cross-reference in both
  directions"* — the tree already has a declared field for this (``amends:``, used
  by 33 ADRs), and **19 of its 36 pairs have no back-pointer today**. The guard is
  red on nineteen other lanes' ADRs on the day it is written, and greening it is
  not this lane's work. It also could not have caught the actual failure: ADR-0206
  never declared that it revised ADR-0172, and a symmetry check has nothing to
  check until someone declares it.
* *"every ``placeholder=True`` capacity is named in the ADR that retires it"* —
  ADR-0206 §8 deletes thirteen and names eight. ``planning.derive_initial_plan``,
  ``planning.aggregate_outputs``, ``decision.signal_to_tier``,
  ``scoring.attention_score`` and ``phase6.attribute_blame`` are unnamed. Greening
  it means editing a Proposed ADR's substance, which belongs to CORE-C4.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

#: Package roots scanned. The `mindsos_*` layers only — `projects/` and the
#: brains are subsystems (RULES §8) and are not core's to police.
_PACKAGES = (
    "mindsos_admin",
    "mindsos_capacity",
    "mindsos_cli",
    "mindsos_core",
    "mindsos_instances",
    "mindsos_intelligence",
    "mindsos_knowledge",
    "mindsos_server",
)

#: Documentation roots scanned, with the two exclusions below.
_DOCS = "docs"

#: `docs/` subtrees NOT scanned, each for a stated reason. Both exempt real
#: files that match a retired token today, so neither is an inert entry
#: (RULES §9: an allowlist entry that exempts nothing is a defect) —
#: :func:`test_exclusions_are_load_bearing` holds them to that.
_DOCS_EXCLUDED: tuple[tuple[str, str], ...] = (
    (
        "docs/decisions/adr/",
        "an ADR is a dated record of a decision as it was made; `about.md` says "
        "do not rewrite it. ADR-0172 carries its pointer as §amendment-2, which "
        "is the mechanism RULES §9 prescribes — not as an edit to its text.",
    ),
    (
        "docs/_workbench/",
        "the workbench is not in `mkdocs.yml`'s nav and is not published; it is "
        "where unfinished thinking is allowed to be wrong.",
    ),
)

#: ``(human name, token pattern, the ADR that retires it)``.
#:
#: ``MAX_DEPTH`` is matched **word-bounded and upper-case** so it does not drag
#: in the pipeline finder's unrelated ``max_depth`` parameter or
#: ``FIND_MAX_DEPTH_EXCEEDED`` (no word boundary inside the latter). The prose
#: form is pinned to the three phrasings the published docs actually use; a
#: fourth phrasing would slip past, which is the honest limit of a text guard
#: and the reason claim 1 is not the whole fix.
RETIRED: tuple[tuple[str, str, str], ...] = (
    (
        "the MAX_DEPTH plan-depth bound (ADR-0206 §4 — confidence is the "
        "stopping rule)",
        r"\bMAX_DEPTH\b|max-depth (?:is|of|=) 3",
        "ADR-0206",
    ),
    (
        "the derive_goal interpretation step (ADR-0206 §3 — the steps are "
        "request -> hint -> map -> plan)",
        r"\bderive_goal\b",
        "ADR-0206",
    ),
)

#: The plan whose item table claim 2 resolves against.
_PLAN = "confirmation_docs/CORE_RECONCILIATION_PLAN.md"

#: The §5 heading and the ids inside it.
_C4_SECTION = re.compile(r"^##\s+\d+\.\s+CORE-C4\b[^\n]*\n(.*?)(?=^##\s)", re.M | re.S)
_C4_DECLARED = re.compile(r"\*\*C4R(\d+)\*\*")
_C4_CITED = re.compile(r"\bC4R(\d+)\b")


def _source_root() -> Path:
    """The directory holding the `mindsos_*` packages, `docs/` and the plan.

    Marker-free on the repo root for the reason
    ``tests/architecture/test_no_subsystem_ownership.py`` gives: the test image
    copies the packages, ``tests/``, ``docs/`` and ``confirmation_docs/`` into
    ``/app`` but not ``RULES.md``, so anchoring on a repo-root marker passes in a
    checkout and fails in the container.
    """
    for parent in Path(__file__).resolve().parents:
        if all((parent / pkg).is_dir() for pkg in _PACKAGES) and (
            parent / _DOCS
        ).is_dir():
            return parent
    try:  # installed rather than laid out beside the tests
        import mindsos_capacity

        candidate = Path(mindsos_capacity.__file__).resolve().parent.parent
        if all((candidate / pkg).is_dir() for pkg in _PACKAGES):
            return candidate
    except Exception:  # noqa: BLE001 - fall through to the explicit error
        pass
    raise RuntimeError(
        "source root not found: no directory above this test contains all of "
        f"{list(_PACKAGES)} plus {_DOCS!r}"
    )


def _scanned_paths(root: Path) -> list[Path]:
    files: list[Path] = []
    for pkg in _PACKAGES:
        files.extend(sorted((root / pkg).rglob("*.py")))
    for path in sorted((root / _DOCS).rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(prefix) for prefix, _ in _DOCS_EXCLUDED):
            continue
        files.append(path)
    return files


def _sources(root: Path | None = None) -> dict[str, str]:
    """``{repo-relative path: file text}`` for every scanned file."""
    root = root or _source_root()
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8", errors="replace")
        for p in _scanned_paths(root)
    }


def _missing_pointers(
    sources: dict[str, str],
    retired: tuple[tuple[str, str, str], ...] = RETIRED,
) -> list[str]:
    """Files naming a retired token without naming its replacement.

    Pure over its inputs so the mutations below run on synthetic sources and
    never touch the tree.
    """
    out: list[str] = []
    for rel, text in sorted(sources.items()):
        for name, pattern, current in retired:
            if re.search(pattern, text) and current not in text:
                out.append(f"{rel}: names {name} but never names {current}")
    return out


def _declared_c4_ids(plan_text: str) -> set[str]:
    section = _C4_SECTION.search(plan_text)
    if section is None:
        raise AssertionError(
            f"{_PLAN}: the CORE-C4 section heading no longer matches — claim 2 "
            "would silently resolve against an empty id set"
        )
    return set(_C4_DECLARED.findall(section.group(1)))


def _dangling_c4(sources: dict[str, str], declared: set[str]) -> list[str]:
    out: list[str] = []
    for rel, text in sorted(sources.items()):
        for num in sorted(set(_C4_CITED.findall(text)), key=int):
            if num not in declared:
                out.append(f"{rel}: cites CORE-C4R{num}, which {_PLAN} §5 does not declare")
    return out


# ── the two claims ───────────────────────────────────────────────────────


def test_retired_tokens_name_the_current_design() -> None:
    problems = _missing_pointers(_sources())
    assert not problems, (
        "a live file describes a retired design without naming the design that "
        "replaced it — this is the 2026-08-20 failure, exactly:\n  "
        + "\n  ".join(problems)
    )


def test_cited_core_c4_items_exist() -> None:
    root = _source_root()
    declared = _declared_c4_ids((root / _PLAN).read_text(encoding="utf-8"))
    problems = _dangling_c4(_sources(root), declared)
    assert not problems, (
        "a pointer to a CORE-C4 item does not resolve:\n  " + "\n  ".join(problems)
    )


# ── the guard cannot disarm itself ───────────────────────────────────────


def test_scan_is_not_empty() -> None:
    """A guard that scans nothing passes forever. Pin that it scans."""
    sources = _sources()
    assert len(sources) > 200, f"only {len(sources)} files scanned — the roots have moved"
    assert any(
        re.search(RETIRED[1][1], text) for text in sources.values()
    ), "no scanned file mentions derive_goal — the scan or the token has drifted"


def test_c4_section_declares_the_items() -> None:
    root = _source_root()
    declared = _declared_c4_ids((root / _PLAN).read_text(encoding="utf-8"))
    assert len(declared) >= 8, (
        f"only {sorted(declared)} declared in {_PLAN} §5 — the table's id format "
        "has changed and claim 2 has stopped policing anything"
    )


def test_exclusions_are_load_bearing() -> None:
    """Each `docs/` exclusion must exempt something a claim would flag.

    Same defect class as the ADR-ownership guard's inert ALLOWLIST: an
    exclusion that exempts nothing is dead text that reads as a real carve-out.
    """
    root = _source_root()
    for prefix, reason in _DOCS_EXCLUDED:
        subtree = root / prefix
        assert subtree.is_dir(), f"{prefix} no longer exists — drop the exclusion"
        exempted = {
            p.relative_to(root).as_posix(): p.read_text(encoding="utf-8", errors="replace")
            for p in sorted(subtree.rglob("*.md"))
        }
        assert _missing_pointers(exempted), (
            f"exclusion {prefix!r} ({reason}) exempts nothing — remove it or the "
            "carve-out is dead text"
        )


# ── mutations: each claim is observed RED ────────────────────────────────


@pytest.mark.parametrize(
    "body",
    ("MAX_DEPTH = 3\n", "Cold-start max-depth is 3, admin-tunable per pattern.\n"),
)
def test_a_max_depth_mention_without_the_pointer_is_reported(body: str) -> None:
    row = RETIRED[0]
    assert _missing_pointers({"fake/module.py": body}, retired=(row,)), (
        f"the guard does not report {body!r} with no ADR-0206"
    )
    assert not _missing_pointers(
        {"fake/module.py": body + "Retired by ADR-0206 §4.\n"}, retired=(row,)
    ), "adding the pointer does not clear the violation"


def test_a_derive_goal_mention_without_the_pointer_is_reported() -> None:
    row = RETIRED[1]
    body = "step 4 dispatches ``decision.derive_goal`` and returns a goal\n"
    assert _missing_pointers({"fake/module.py": body}, retired=(row,))
    assert not _missing_pointers(
        {"fake/module.py": body + "Retired by ADR-0206 §3.\n"}, retired=(row,)
    ), "adding the pointer does not clear the violation"


def test_a_dangling_c4_id_is_reported() -> None:
    declared = {"1", "2", "3", "4", "5", "6", "7", "8"}
    assert _dangling_c4({"fake/module.py": "unbuilt CORE work — CORE-C4R99."}, declared)
    assert not _dangling_c4({"fake/module.py": "unbuilt CORE work — CORE-C4R7."}, declared)


def test_the_finder_max_depth_is_not_dragged_in() -> None:
    """`FIND_MAX_DEPTH_EXCEEDED` and the finder's `max_depth` are a different
    thing entirely (ADR-0206 §3 retires neither). A guard that flagged them
    would be routed around within a week."""
    unrelated = {
        "mindsos_capacity/pipeline.py": (
            'FIND_MAX_DEPTH_EXCEEDED = "max_depth_exceeded"\n'
            "def find_pipeline(start, target, max_depth=6): ...\n"
        ),
        "docs/usage/capacity/retrieval.md": "`mindsos capacity find [--max-depth N]`\n",
    }
    assert not _missing_pointers(unrelated)
