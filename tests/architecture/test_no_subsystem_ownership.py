"""Guard — no `mindsos_*` module may name a subsystem as the owner of core work.

ADR-0205 §8 + `RULES.md` §8: a subsystem or brain (WSD, FOL, DWF, NLU, a demo,
a brain) is a **consumer** of MindsOS. It never owns, ships or gates a core
mechanism. If core is missing something, core builds it.

The rule already existed in `RULES.md` and did not hold, because 24 docstrings
inside `mindsos_*` said the opposite and a chat reads the file it is editing,
not the repo root. The recorded lesson from the 2026-06-25 ownership pass:
*"chats believe ARTIFACTS, not rules."* This test makes the artifact enforce it.

A placeholder records **what is missing** and **which CR tracks it** — never who
will ship it.

Adding a legitimate exception: append to :data:`ALLOWLIST` with the reason, and
only when the mention is a subsystem acting as a *consumer* or as a genuine
subsystem-owned identifier — never to re-admit an ownership claim. An entry that
exempts nothing fails :func:`test_allowlist_entries_are_load_bearing`.

2026-08-01 audit (CORE-C1R4 follow-on). The guard was verified to actually bite
— it scans 226 files and :func:`test_package_is_scanned` already defended the
scan-zero failure mode. Two defects were found and fixed:

  * **Coverage was narrow enough to miss the phrasings people use.** Of fourteen
    plausible ownership claims probed, fourteen slipped through — including
    ``"WSD ships the real catalog"`` (the pattern required the literal "ships
    *in*"), ``"owned by WSD"`` (only the hyphenated ``WSD-owned`` matched), and
    ``"deferred to WSD"`` / ``"routed to WSD"``. That last pair is the one that
    matters: RULES §8's own text is *"Stop deferring core mechanics 'to WSD'"*.
    Five patterns added; all five were verified to produce **zero** hits across
    the scanned packages, so broadening cost no cleanup.
  * **The ALLOWLIST was inert and its staleness test could not tell.** All five
    entries exempted text that no pattern flagged, so the raw hit count before
    allowlisting was already zero. The old ``test_allowlist_entries_still_exist``
    asserted the exempted *text* still existed, not that the entry was *needed*
    — so an allowlist can rot to 100% inert and stay green. That is the same
    defect class as the ADR status guard (which asserted agreement on rows it
    was silently never reading). The entries are removed and the test now
    asserts each entry is **load-bearing**: delete it, and a violation must
    appear.

:data:`_PROBES` pins the phrasings the patterns must catch, so a future
refactor cannot quietly narrow them.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

#: Package roots scanned. The `mindsos_*` layers only — `projects/` and the
#: brains are subsystems and may name themselves freely.
_PACKAGES = (
    "mindsos_admin",
    "mindsos_capacity",
    "mindsos_cli",
    "mindsos_core",
    "mindsos_instances",
    "mindsos_intelligence",
    "mindsos_llm",
    "mindsos_knowledge",
    "mindsos_server",
)

#: Subsystem / brain names that must never appear as an owner of core work.
_SUBSYSTEMS = ("WSD", "FOL", "DWF", "NLU", "arc", "nilm", "bongard", "robot")

_SUB = "|".join(_SUBSYSTEMS)

#: Phrasings that assert a subsystem owns, ships or gates core work.
_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(rf"\b(?:{_SUB})\b[ -]?installation\b", re.IGNORECASE),
    re.compile(rf"\bships? in\s+(?:{_SUB})\b", re.IGNORECASE),
    re.compile(rf"\b(?:{_SUB})\s+replaces\b", re.IGNORECASE),
    re.compile(rf"\b(?:{_SUB})[- ]gated\b", re.IGNORECASE),
    re.compile(rf"\bland(?:s|ing)? (?:with|in)\s+(?:{_SUB})\b", re.IGNORECASE),
    re.compile(rf"\b(?:{_SUB})[- ]owned\b", re.IGNORECASE),
    # ── added 2026-08-01, each verified zero-hit on the scanned packages ──
    re.compile(
        rf"\b(?:{_SUB})\b[^.\n]{{0,40}}\b(?:ships?|will ship|shipped by)\b",
        re.IGNORECASE,
    ),
    re.compile(rf"\bowned by\s+(?:{_SUB})\b", re.IGNORECASE),
    re.compile(
        rf"\b(?:deferred|routed|blocked|pending|waiting)\s+(?:to|on|for)?\s*"
        rf"(?:{_SUB})\b",
        re.IGNORECASE,
    ),
    re.compile(rf"\b(?:{_SUB})\b[^.\n]{{0,30}}\bresponsible\b", re.IGNORECASE),
    re.compile(
        rf"\b(?:{_SUB})\b[^.\n]{{0,20}}\b(?:provides|owns)\b", re.IGNORECASE
    ),
    # Verb-then-subsystem — the mirror of the two patterns above, which only
    # match when the subsystem precedes the verb ("WSD ships X" but not
    # "will ship with WSD").
    re.compile(
        rf"\b(?:ships?|shipped|shipping|will ship|lands?|landing)\b[^.\n]{{0,25}}"
        rf"\b(?:with|by|in|to)\s+(?:the\s+)?(?:{_SUB})\b",
        re.IGNORECASE,
    ),
)

#: Phrasings the patterns MUST catch. Pins coverage against silent narrowing.
_PROBES: tuple[str, ...] = (
    "WSD installation ships this",
    "this ships in WSD",
    "WSD replaces the v0 catalog",
    "WSD-gated until phase 54",
    "lands with WSD",
    "WSD-owned catalog",
    "WSD ships the real catalog",
    "this will ship with DWF",
    "owned by WSD",
    "deferred to WSD",
    "routed to WSD",
    "blocked on WSD",
    "WSD is responsible for this",
    "the nilm brain owns this",
    "FOL provides the rule confidences",
    "will ship with the arc brain",
    "shipped by WSD",
)

#: (relative path, substring) pairs that are legitimate and must not fail.
#: Each entry states WHY. Quotations of a historical ADR clause are allowed
#: only where the surrounding text marks the attribution as wrong.
#:
#: Empty as of 2026-08-01: the five prior entries exempted text that no pattern
#: flagged, so none was load-bearing. See the module docstring.
ALLOWLIST: tuple[tuple[str, str], ...] = ()


def _source_root() -> Path:
    """The directory containing the `mindsos_*` packages.

    Marker-free on purpose. The test image copies the packages + ``tests`` into
    ``/app`` but **not** ``RULES.md`` or ``projects/`` (see ``Dockerfile``), so
    anchoring on a repo-root marker passes in a checkout and fails in the
    container. Anchoring on the packages themselves works in both.
    """
    for parent in Path(__file__).resolve().parents:
        if all((parent / pkg).is_dir() for pkg in _PACKAGES):
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
        f"{list(_PACKAGES)}"
    )


def _python_files() -> list[Path]:
    root = _source_root()
    files: list[Path] = []
    for pkg in _PACKAGES:
        files.extend(sorted((root / pkg).rglob("*.py")))
    return files


def _scanned_sources() -> dict[str, str]:
    """``{repo-relative path: file text}`` for every scanned module."""
    root = _source_root()
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in _python_files()
    }


def _allowed(
    rel: str,
    text: str,
    span: tuple[int, int],
    allowlist: tuple[tuple[str, str], ...],
) -> bool:
    """True when this hit is covered by an allowlist entry in the same file."""
    window = text[max(0, span[0] - 200) : span[1] + 200]
    for allow_rel, needle in allowlist:
        if rel == allow_rel and needle in window:
            return True
    return False


def _violations(
    sources: dict[str, str],
    allowlist: tuple[tuple[str, str], ...] = ALLOWLIST,
) -> list[str]:
    """Ownership claims in *sources* not covered by *allowlist*.

    Pure over its inputs so the allowlist mechanism itself can be tested
    without touching the repo.
    """
    out: list[str] = []
    for rel, text in sources.items():
        for pattern in _PATTERNS:
            for match in pattern.finditer(text):
                if _allowed(rel, text, match.span(), allowlist):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                out.append(f"{rel}:{line}: {match.group(0)!r}")
    return out


def test_no_subsystem_named_as_owner_of_core_work() -> None:
    violations = _violations(_scanned_sources())
    assert not violations, (
        "A `mindsos_*` module names a subsystem as the owner/shipper/gate of core "
        "work. A subsystem is a CONSUMER (RULES §8, ADR-0205 §8); core builds its "
        "own mechanisms. Record WHAT is missing and WHICH CR tracks it — never who "
        "will ship it. If a hit is legitimate, add it to ALLOWLIST with a reason.\n"
        + "\n".join(violations)
    )


def test_patterns_catch_known_phrasings() -> None:
    """Pin coverage. A refactor must not silently narrow the patterns.

    The 2026-08-01 audit found fourteen plausible ownership claims slipping
    through, including the one RULES §8 names verbatim ("deferring core
    mechanics 'to WSD'"). These probes stop that regressing.
    """
    missed = [p for p in _PROBES if not any(r.search(p) for r in _PATTERNS)]
    assert not missed, (
        "these ownership phrasings are no longer caught by any pattern:\n  "
        + "\n  ".join(repr(m) for m in missed)
    )


def test_allowlist_entries_are_load_bearing() -> None:
    """Every ALLOWLIST entry must actually exempt a real hit.

    The prior version asserted the exempted *text* still existed, which an
    entry can satisfy while exempting nothing — and all five entries did
    exactly that. Removing an entry must produce a violation; if it does not,
    the entry is dead and should be deleted rather than left implying an
    exception is in force.
    """
    sources = _scanned_sources()
    inert: list[str] = []
    for entry in ALLOWLIST:
        without = tuple(e for e in ALLOWLIST if e != entry)
        if len(_violations(sources, without)) == len(_violations(sources, ALLOWLIST)):
            inert.append(f"{entry[0]}: {entry[1]!r}")
    assert not inert, (
        "ALLOWLIST entries that exempt nothing — delete them, they document an "
        "exception that is not in force:\n  " + "\n  ".join(inert)
    )


def test_allowlist_mechanism_exempts_and_stops_exempting() -> None:
    """The allowlist must be able to both exempt and not-exempt.

    ``test_allowlist_entries_are_load_bearing`` is vacuous while ALLOWLIST is
    empty, so prove the mechanism on synthetic input instead. Without this, an
    empty allowlist would let a broken ``_allowed`` sit undetected until the
    first real exception needed it.
    """
    rel = "mindsos_core/_synthetic.py"
    sources = {rel: '"""A placeholder; this ships in WSD until the catalog lands."""'}

    assert _violations(sources, ()), "synthetic violation not detected at all"
    assert not _violations(sources, ((rel, "until the catalog lands"),)), (
        "an allowlist entry near the hit failed to exempt it"
    )
    other_file = (("mindsos_core/other.py", "until the catalog lands"),)
    assert _violations(sources, other_file), (
        "an allowlist entry for a DIFFERENT file wrongly exempted the hit"
    )
    assert _violations(sources, ((rel, "text that is not present"),)), (
        "an allowlist entry whose needle is absent wrongly exempted the hit"
    )


def test_scan_reads_a_plausible_number_of_files() -> None:
    """Guard against the guard silently scanning nothing.

    ``test_package_is_scanned`` proves the directories exist; this proves files
    were actually read from them. The ADR status guard failed for exactly this
    reason — it checked zero rows and reported success.
    """
    sources = _scanned_sources()
    assert len(sources) > 100, (
        f"only {len(sources)} module(s) scanned — the package layout changed and "
        "the guard is no longer reading the source tree"
    )


@pytest.mark.parametrize("pkg", _PACKAGES)
def test_package_is_scanned(pkg: str) -> None:
    """Fail loudly if a package moved or was renamed, rather than scanning zero."""
    assert (_source_root() / pkg).is_dir(), f"{pkg} not found — update _PACKAGES"


def test_every_mindsos_package_present_is_LISTED_not_merely_scanned() -> None:
    """The inverse of :func:`test_package_is_scanned` — the half that was missing.

    :func:`test_package_is_scanned` asks *"does each LISTED package exist?"*. It
    is parametrized over :data:`_PACKAGES`, so **deleting a name from that tuple
    deletes the question along with it.**

    Measured 2026-09-03 by the RULES §12.2 sweep of ADR-0210 slice 1: removing
    ``"mindsos_llm"`` from :data:`_PACKAGES` reddened **nothing** — the guard
    simply stopped scanning the newest package, ``test_package_is_scanned``
    collected one case fewer, and :func:`test_scan_reads_a_plausible_number_of_files`
    was far too loose to notice one package's worth of files. The same shape ran
    the other way in the same ship: adding ``mindsos_llm`` widened this file by a
    silent ``+1`` that the ship's own collect arithmetic never accounted for.

    A hand-listed domain that can be silenced by shrinking it is the shape filed
    as ``dr-guard-domains-pinned-to-lists`` — this was its fourth instance and
    its first in core. So the question is asked from the FILESYSTEM too, which is
    the same repair ``tests/phase_28`` and
    ``tests/llm_seam/test_import_isolation_mindsos_llm.py`` already carry.

    The tuple is kept rather than derived, because it also documents intent
    (``projects/`` and the brains are subsystems and are deliberately out of
    scope). What changes is that it can no longer be quietly narrowed.
    """
    present = {
        d.name
        for d in _source_root().iterdir()
        if d.is_dir()
        and d.name.startswith("mindsos_")
        and (d / "__init__.py").exists()
    }
    missing = sorted(present - set(_PACKAGES))
    assert missing == [], (
        f"{missing} ship as mindsos_* packages and are absent from _PACKAGES, so "
        "this guard does not scan them at all. Add them. A domain nobody widened "
        "is a domain that silently stopped asking."
    )
