"""Phase 34 — ``docs/dev/review-checklist.md`` exists (ADR-0143 §Accept (c))."""

from __future__ import annotations

import os
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_CHECKLIST_PATH = _REPO_ROOT / "docs" / "dev" / "review-checklist.md"


def test_review_checklist_file_exists():
    """ADR-0143 §Accept criterion (c) — file must exist for Status flip."""
    assert _CHECKLIST_PATH.exists(), (
        f"Review checklist missing at {_CHECKLIST_PATH}; required by "
        "ADR-0143 §Accept criterion (c) for Proposed → Accepted flip."
    )


def test_review_checklist_mentions_never_mutates_rule():
    """ADR-0143 §Constraint must be the headline rule."""
    text = _CHECKLIST_PATH.read_text(encoding="utf-8")
    assert "never mutates" in text.lower() or "never-mutates" in text.lower()
    assert "KLWriteHandle" in text


def test_review_checklist_contains_three_items():
    """R1 PB-D: 3 items (never-mutates + outputs=() + context-based session/kl)."""
    text = _CHECKLIST_PATH.read_text(encoding="utf-8")
    # Item markers are markdown headers OR numbered list — count by
    # the load-bearing phrases.
    assert "KLWriteHandle" in text  # item 1
    assert "outputs=()" in text or "outputs == ()" in text  # item 2
    assert "context" in text and "session" in text  # item 3
