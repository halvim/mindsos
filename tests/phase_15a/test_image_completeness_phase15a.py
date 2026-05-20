"""Phase 15a — 6 new sentinel paths exist (mindsos_admin/ package).

The root-level ``tests/test_image_completeness.py`` already parametrises
over the cumulative ``tests/_shared/sentinel_paths.py`` list; Phase 15a
adds 6 entries (7-site new-top-level-package checklist site #3 + #7).
This module gives a phase-scoped checkpoint that the Phase 15a sentinel
rows are tracked.
"""

from __future__ import annotations

import os

import pytest


_PHASE_15A_NEW_PATHS = (
    "mindsos_admin/__init__.py",
    "mindsos_admin/bootstrap.py",
    "mindsos_admin/importers/__init__.py",
    "mindsos_admin/importers/dolce.py",
    "mindsos_admin/importers/oewn.py",
    "mindsos_admin/importers/framenet.py",
)


@pytest.mark.parametrize("rel_path", _PHASE_15A_NEW_PATHS)
def test_phase_15a_sentinel_path_exists(rel_path: str) -> None:
    """The 6 Phase 15a NEW module files exist relative to repo root."""
    repo_root = os.environ.get("MINDSOS_REPO_ROOT", os.getcwd())
    full = os.path.join(repo_root, rel_path)
    assert os.path.exists(full), (
        f"Phase 15a sentinel path missing: {full!r}"
    )


def test_sentinel_paths_list_includes_phase_15a() -> None:
    """The cumulative SENTINEL_PATHS list contains all 6 Phase 15a entries."""
    from tests._shared.sentinel_paths import SENTINEL_PATHS

    for path in _PHASE_15A_NEW_PATHS:
        assert path in SENTINEL_PATHS, (
            f"Phase 15a path {path!r} missing from SENTINEL_PATHS"
        )
