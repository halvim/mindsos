"""Phase tarball retention-window logic.

Pure-Python so the workflow's retention step is testable without GitHub access.
The release workflow shells out to `gh api` + `jq`, but the SELECTION logic
(which phases to keep, which to evict) lives here and is unit-tested.

Tag grammar (PHASE_MAP §1, "Phase rollback / supersession"):

    phase-NN-confirmed                 — original confirmed tag for phase NN.
    phase-NN-vM-confirmed              — supersession M (M >= 2) for phase NN.

Retention rules:

    1. The "slot" a tag occupies is its phase number NN. Multiple tags for the
       same NN (the original plus zero-or-more `-vM-`) all share one slot.
    2. Within a slot, the highest-version tag is the install target; older
       tags' tarballs are evicted regardless of the 5-phase window. (The
       Release records remain — only the tarball asset is replaced.)
    3. Across slots, the `window` highest-numbered slots keep their install-
       target tarball; older slots evict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Matches both `phase-NN-confirmed` and `phase-NN-vM-confirmed` (M >= 2).
_TAG_RE = re.compile(r"^phase-(\d{1,3})(?:-v(\d+))?-confirmed$")


@dataclass(frozen=True)
class TagInfo:
    """Parsed components of a confirmed-phase tag."""

    tag: str
    phase: int
    version: int  # 1 for the original; >=2 for `-vM-` supersessions.


@dataclass(frozen=True)
class RetentionDecision:
    """Result of running the retention selector over a list of confirmed tags."""

    keep: list[str]
    """Tags whose tarball asset should remain. Sorted descending by phase, then version."""

    evict: list[str]
    """Tags whose tarball asset should be replaced with a placeholder. Sorted descending."""


def parse_tag(tag: str) -> TagInfo | None:
    """Return parsed components for a confirmed-phase tag, or None."""
    m = _TAG_RE.match(tag)
    if not m:
        return None
    phase = int(m.group(1))
    version = int(m.group(2)) if m.group(2) else 1
    return TagInfo(tag=tag, phase=phase, version=version)


def parse_phase_number(tag: str) -> int | None:
    """Back-compat shim — returns the phase number or None."""
    info = parse_tag(tag)
    return info.phase if info else None


def select_retention(
    confirmed_tags: list[str], window: int = 5
) -> RetentionDecision:
    """Pick which confirmed-phase tags keep their tarball asset.

    Two-phase logic:

        1. Per slot: highest-version tag wins (the install target). Older
           supersession tags within the same slot evict immediately.
        2. Across slots: `window` highest-numbered slots' install targets are
           kept; older slots' install targets evict.

    `confirmed_tags` may contain non-matching tags; they are ignored.
    Returns lists sorted by phase descending, then version descending.

    Examples:
        >>> select_retention(["phase-00-confirmed"]).keep
        ['phase-00-confirmed']
        >>> r = select_retention(
        ...     ["phase-01-confirmed", "phase-01-v2-confirmed"], window=5
        ... )
        >>> r.keep, r.evict
        (['phase-01-v2-confirmed'], ['phase-01-confirmed'])
    """
    if window < 0:
        raise ValueError(f"window must be non-negative, got {window}")

    parsed = [info for info in (parse_tag(t) for t in confirmed_tags) if info]

    # Step 1: group by phase, pick highest-version per slot.
    by_phase: dict[int, list[TagInfo]] = {}
    for info in parsed:
        by_phase.setdefault(info.phase, []).append(info)

    install_targets: list[TagInfo] = []
    superseded: list[TagInfo] = []
    for phase, tags in by_phase.items():
        tags_sorted = sorted(tags, key=lambda i: i.version, reverse=True)
        install_targets.append(tags_sorted[0])
        superseded.extend(tags_sorted[1:])

    # Step 2: keep top `window` install targets by phase number.
    install_targets.sort(key=lambda i: i.phase, reverse=True)
    kept_targets = install_targets[:window]
    evicted_targets = install_targets[window:]

    keep = [i.tag for i in kept_targets]
    # Evict superseded + outside-window install targets, sorted desc by (phase, version).
    evict_pool = superseded + evicted_targets
    evict_pool.sort(key=lambda i: (i.phase, i.version), reverse=True)
    evict = [i.tag for i in evict_pool]

    return RetentionDecision(keep=keep, evict=evict)
