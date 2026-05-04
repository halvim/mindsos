"""Image-completeness regression guard (gg / φ-class) — root-level cumulative test.

Phase 02 introduced this guard at ``tests/phase_02/test_image_completeness.py``.
Phase 03 relocates it to the root (no longer phase-scoped) with the
sentinel list extracted to ``tests/_shared/sentinel_paths.py``. Each
phase that adds a new static input the CLI reads at runtime appends to
the shared list there.

History: Phase 01 §10.1 — Dockerfile drift caused 10 in-container test
failures incl. a Phase 00 regression. This test catches such drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._shared.sentinel_paths import SENTINEL_PATHS


def _repo_root() -> Path:
    """Return the repo root by walking up to find pyproject.toml."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


@pytest.fixture
def repo_root() -> Path:
    return _repo_root()


@pytest.mark.parametrize("relpath", SENTINEL_PATHS)
def test_sentinel_file_is_present(repo_root, relpath):
    path = repo_root / relpath
    assert path.exists(), (
        f"image-completeness regression: {relpath!r} is missing from "
        f"{repo_root!r}. If you added a new static input that the CLI reads "
        "at runtime, also COPY it in the Dockerfile (both prod and test "
        "stages) and append it to SENTINEL_PATHS in tests/_shared/sentinel_paths.py."
    )
    # Non-empty too, so an accidental zero-byte placeholder is caught.
    assert path.stat().st_size > 0, f"{relpath} is zero-byte"
