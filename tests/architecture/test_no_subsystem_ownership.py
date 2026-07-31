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
subsystem-owned identifier — never to re-admit an ownership claim.
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
)

#: (relative path, substring) pairs that are legitimate and must not fail.
#: Each entry states WHY. Quotations of a historical ADR clause are allowed
#: only where the surrounding text marks the attribution as wrong.
ALLOWLIST: tuple[tuple[str, str], ...] = (
    (
        "mindsos_intelligence/als_subsystems.py",
        "wsd-candidate-scorer",
        # A genuine WSD-owned subsystem identifier, not a core mechanism.
    ),
    (
        "mindsos_capacity/family_rules.py",
        "WSD / FOL / code-skill / adapter",
        # Names installing chats as consumers, which is correct.
    ),
    (
        "mindsos_intelligence/capacity_persister.py",
        'live-only until WSD" clause',
        # Quotes ADR-0202's clause name; the surrounding text marks it a
        # misattribution and cites RULES §8.
    ),
    (
        "mindsos_intelligence/mm_persister.py",
        'live-only until\n  WSD" clause',
        # Same ADR-0202 quotation, same correction alongside it.
    ),
    (
        "mindsos_intelligence/consolidation.py",
        'capacity_mm live-only until WSD" clause',
        # Same ADR-0202 quotation, same correction alongside it.
    ),
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "RULES.md").exists():
            return parent
    raise RuntimeError("repo root not found (no RULES.md above this test)")


def _python_files() -> list[Path]:
    root = _repo_root()
    files: list[Path] = []
    for pkg in _PACKAGES:
        files.extend(sorted((root / pkg).rglob("*.py")))
    return files


def _allowed(rel: str, text: str, span: tuple[int, int]) -> bool:
    """True when this hit is covered by an allowlist entry in the same file."""
    window = text[max(0, span[0] - 200) : span[1] + 200]
    for allow_rel, needle in ALLOWLIST:
        if rel == allow_rel and needle in window:
            return True
    return False


def test_no_subsystem_named_as_owner_of_core_work() -> None:
    root = _repo_root()
    violations: list[str] = []

    for path in _python_files():
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for pattern in _PATTERNS:
            for match in pattern.finditer(text):
                if _allowed(rel, text, match.span()):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                violations.append(f"{rel}:{line}: {match.group(0)!r}")

    assert not violations, (
        "A `mindsos_*` module names a subsystem as the owner/shipper/gate of core "
        "work. A subsystem is a CONSUMER (RULES §8, ADR-0205 §8); core builds its "
        "own mechanisms. Record WHAT is missing and WHICH CR tracks it — never who "
        "will ship it. If a hit is legitimate, add it to ALLOWLIST with a reason.\n"
        + "\n".join(violations)
    )


def test_allowlist_entries_still_exist() -> None:
    """An allowlist entry whose text is gone is stale and must be removed."""
    root = _repo_root()
    stale: list[str] = []
    for rel, needle in ALLOWLIST:
        path = root / rel
        if not path.exists():
            stale.append(f"{rel} (file missing)")
            continue
        if needle not in path.read_text(encoding="utf-8"):
            stale.append(f"{rel}: {needle!r}")

    assert not stale, (
        "Stale ALLOWLIST entries — the exempted text no longer exists. Remove "
        "them so the allowlist stays an accurate record of real exceptions.\n"
        + "\n".join(stale)
    )


@pytest.mark.parametrize("pkg", _PACKAGES)
def test_package_is_scanned(pkg: str) -> None:
    """Fail loudly if a package moved or was renamed, rather than scanning zero."""
    assert (_repo_root() / pkg).is_dir(), f"{pkg} not found — update _PACKAGES"
