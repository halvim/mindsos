"""Phase 14 — 3 new sentinel paths exist (knowledge_layer, metagraph_view, bootstrap).

The root-level ``tests/test_image_completeness.py`` already parametrises
over the cumulative ``tests/_shared/sentinel_paths.py`` list; Phase 14
adds 3 entries. This module gives a phase-scoped checkpoint that the
Phase 14 sentinel rows are tracked.
"""

from __future__ import annotations

import os

import pytest


_PHASE_14_NEW_PATHS = (
    "mindsos_knowledge/knowledge_layer.py",
    "mindsos_knowledge/metagraph_view.py",
    "mindsos_knowledge/bootstrap.py",
)


@pytest.mark.parametrize("rel_path", _PHASE_14_NEW_PATHS)
def test_phase_14_sentinel_path_exists(rel_path: str) -> None:
    """The 3 Phase 14 NEW module files exist relative to repo root."""
    # MINDSOS_REPO_ROOT env var is set by `mindsos_cli.commands` runtime;
    # in tests, the cwd is the repo root.
    repo_root = os.environ.get("MINDSOS_REPO_ROOT", os.getcwd())
    full = os.path.join(repo_root, rel_path)
    assert os.path.exists(full), (
        f"Phase 14 sentinel path missing: {full!r}"
    )


def test_sentinel_paths_list_includes_phase_14() -> None:
    """The cumulative SENTINEL_PATHS list contains the 3 Phase 14 entries."""
    from tests._shared.sentinel_paths import SENTINEL_PATHS

    for path in _PHASE_14_NEW_PATHS:
        assert path in SENTINEL_PATHS, (
            f"Phase 14 sentinel {path!r} not in cumulative list."
        )
