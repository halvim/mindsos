"""Phase 42 — Model C doc build guard (PB-16, Option B).

`mkdocs build --strict` currently fails on ~17 PRE-EXISTING broken-link
/ missing-nav warnings inherited from the server-pivot era — none
TYPE_COMPAT- or Phase-42-related, and Phase 42 introduces no new ones
(PHASE_42_DESIGN_LOG §8 / PB-16). Per Option B the strict-lift is scoped
to Phase 42's own surface: this is a **no-regression guard** asserting
the non-strict build still completes (i.e. Phase 42's capacity-doc scrub
left the site buildable), not a full strict-clean. The pre-existing
strict warnings are tracked as a separate docs-maintenance item.

Skips when mkdocs is not installed in the test environment.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import pathlib

import pytest

mkdocs = pytest.importorskip("mkdocs")

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_mkdocs_non_strict_build_succeeds():
    with tempfile.TemporaryDirectory() as site_dir:
        proc = subprocess.run(
            [sys.executable, "-m", "mkdocs", "build", "--site-dir", site_dir],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, (
            "mkdocs non-strict build failed (Phase 42 regression?):\n"
            + proc.stderr[-2000:]
        )


def test_no_phase42_retired_terms_break_links():
    # Guard: Phase 42's doc scrub must not have introduced a dangling link
    # to the retired discovery surface. We assert the live capacity usage
    # pages no longer advertise TYPE_COMPAT auto-discovery as current.
    usage = _REPO_ROOT / "docs" / "usage" / "capacity"
    for page in ("overview.md", "building.md", "retrieval.md", "categories.md"):
        text = (usage / page).read_text(encoding="utf-8")
        assert "TYPE_COMPAT" not in text, (
            f"{page} still references TYPE_COMPAT as current behaviour"
        )
