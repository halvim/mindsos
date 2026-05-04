"""Phase 02 — image-completeness regression guard (gg / φ-class).

Phase 01 §10.1 surfaced a Dockerfile drift where `.github/`,
`docker-compose.yml`, and `confirmation_docs/` were not COPYed into the
prod / test image. The result: 10 in-container test failures including a
Phase 00 regression.

This test asserts that every static input the CLI commands rely on is
present at the resolved repo root — which inside the container is
``MINDSOS_REPO_ROOT=/app``. It runs unconditionally; outside the
container it self-checks against the host repo and is therefore an
equally valid host-side guard.

The sentinel list grows with every phase that adds a new static input.
Update this manifest when a new file goes into the Dockerfile COPY list.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# Sentinel files that MUST be reachable from MINDSOS_REPO_ROOT.
# Phase 00 — Dockerfile, compose, manifest, CLI source.
# Phase 01 — workflows, confirmation_docs, _template_notes.
# Phase 02 — mindsos_core (slim identity), Phase 02 tests dir.
_SENTINEL_PATHS = (
    "pyproject.toml",
    "docker-compose.yml",
    "mindsos_cli/manifest.toml",
    "mindsos_cli/app.py",
    "mindsos_cli/commands/doctor.py",
    "mindsos_cli/commands/confirm_phase.py",
    "mindsos_cli/commands/identity.py",  # Phase 02
    "mindsos_core/__init__.py",  # Phase 02
    "mindsos_core/exceptions.py",  # Phase 02
    "mindsos_core/models/__init__.py",  # Phase 02
    "mindsos_core/models/identity.py",  # Phase 02
    ".github/workflows/phase-ci.yml",  # Phase 01
    ".github/workflows/release.yml",  # Phase 01
    "confirmation_docs/_template_notes.md",  # Phase 01
    "confirmation_docs/PHASE_MAP.md",
)


@pytest.fixture
def repo_root(repo_root: Path) -> Path:
    return repo_root


@pytest.mark.parametrize("relpath", _SENTINEL_PATHS)
def test_sentinel_file_is_present(repo_root, relpath):
    path = repo_root / relpath
    assert path.exists(), (
        f"image-completeness regression: {relpath!r} is missing from "
        f"{repo_root!r}. If you added a new static input that the CLI reads "
        "at runtime, also COPY it in the Dockerfile (both prod and test "
        "stages) and append it to _SENTINEL_PATHS in this test."
    )
    # Non-empty too, so an accidental zero-byte placeholder is caught.
    assert path.stat().st_size > 0, f"{relpath} is zero-byte"
