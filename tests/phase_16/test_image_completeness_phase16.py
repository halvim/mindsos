"""Phase 16 — 3 new sentinel paths exist (mindsos_admin/ additions).

The root-level ``tests/test_image_completeness.py`` already parametrises
over the cumulative ``tests/_shared/sentinel_paths.py`` list; Phase 16
adds 3 entries to the existing ``mindsos_admin/`` top-level package
(no new top-level — Dockerfile's existing ``COPY mindsos_admin`` picks
them up automatically). This module gives a phase-scoped checkpoint
that the Phase 16 sentinel rows are tracked.
"""

from __future__ import annotations

import os

import pytest


_PHASE_16_NEW_PATHS = (
    "mindsos_admin/similarity.py",
    "mindsos_admin/_content_hash.py",
    "mindsos_admin/exceptions.py",
)


@pytest.mark.parametrize("rel_path", _PHASE_16_NEW_PATHS)
def test_phase_16_sentinel_path_exists(rel_path: str) -> None:
    """The 3 Phase 16 NEW module files exist relative to repo root."""
    repo_root = os.environ.get("MINDSOS_REPO_ROOT", os.getcwd())
    full = os.path.join(repo_root, rel_path)
    assert os.path.exists(full), (
        f"Phase 16 sentinel path missing: {full!r}"
    )


def test_sentinel_paths_list_includes_phase_16() -> None:
    """The cumulative SENTINEL_PATHS list contains all 3 Phase 16 entries."""
    from tests._shared.sentinel_paths import SENTINEL_PATHS

    for path in _PHASE_16_NEW_PATHS:
        assert path in SENTINEL_PATHS, (
            f"Phase 16 path {path!r} missing from SENTINEL_PATHS"
        )
