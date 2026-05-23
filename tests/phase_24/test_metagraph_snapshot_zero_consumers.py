"""MetagraphSnapshot has zero consumers in halvim — drift guard (PB-Z4(b)).

Per Phase 24 design log PB-13(a) + PB-Z4(b) — the lint rule was
dropped in favour of this zero-consumer assertion test. Phase 23
retirement §7 #4 carry-forward re-opened at PB-13(a).

The module ``mindsos_core/metagraph_snapshot.py`` is retained as a
defensive Core primitive (ADR-0129 §am2) but has no v1 consumer.
This test asserts that consumer-state continues to be zero. New
consumers can legitimately adopt the module by deleting this test
and documenting the use in ADR-0129.
"""

from __future__ import annotations

import re
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[2]

# Match call expressions like `MetagraphSnapshot.of(...)` or
# `MetagraphSnapshot.restore_into(...)`.
_PATTERN = re.compile(r"\bMetagraphSnapshot\s*\.\s*(of|restore_into)\s*\(")


def _scan_for_metagraph_snapshot_use() -> list[tuple[Path, int, str]]:
    """Find all live call-sites of MetagraphSnapshot.{of,restore_into}.

    Excludes:
    * ``mindsos_core/metagraph_snapshot.py`` (the module itself).
    * ``tests/`` (tests of the module are exempt).
    * Anything under ``__pycache__``.

    Returns ``(path, line_number, line)`` tuples.
    """
    matches: list[tuple[Path, int, str]] = []
    for pkg in (
        "mindsos_admin",
        "mindsos_capacity",
        "mindsos_cli",
        "mindsos_core",
        "mindsos_instances",
        "mindsos_knowledge",
        "mindsos_server",
    ):
        pkg_dir = PKG_ROOT / pkg
        if not pkg_dir.is_dir():
            continue
        for py in pkg_dir.rglob("*.py"):
            if "__pycache__" in py.parts:
                continue
            # The defining module itself is exempt.
            if py.name == "metagraph_snapshot.py":
                continue
            text = py.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if _PATTERN.search(line):
                    matches.append((py, lineno, line))
    return matches


def test_no_consumers_of_metagraph_snapshot():
    """ADR-0129 §am2 — zero consumers; module is defensive Core primitive only."""
    matches = _scan_for_metagraph_snapshot_use()
    assert matches == [], (
        f"FORBIDDEN: MetagraphSnapshot.{{of,restore_into}} used "
        f"outside mindsos_core/metagraph_snapshot.py. "
        f"Per ADR-0129 §am2 + Phase 24 PB-13(a), the module is "
        f"retained as a defensive Core primitive with zero v1 "
        f"consumers. If a new feature legitimately adopts the "
        f"module, delete this test and document the use in "
        f"ADR-0129. Found uses:\n"
        + "\n".join(
            f"  {path.relative_to(PKG_ROOT)}:{lineno}: {line.strip()}"
            for path, lineno, line in matches
        )
    )
