"""Tier 6 — Phase 12 sentinel-paths additions.

Parametrised over the Phase 12 entries appended to
`tests/_shared/sentinel_paths.py`. Per
`feedback_sentinel_paths_runtime_only.md`: only runtime Python modules
COPYd into both Dockerfile prod + test stages. The 3 new entries are:

* mindsos_knowledge/__init__.py
* mindsos_knowledge/identifiers.py
* mindsos_knowledge/exceptions.py

All three import at CLI runtime (mindsos_cli.commands.knowledge
imports from mindsos_knowledge).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# Runtime root inside the container; falls back to the repo root on Mac.
_REPO_ROOT_ENV = os.environ.get("MINDSOS_REPO_ROOT")
_REPO_ROOT = (
    Path(_REPO_ROOT_ENV)
    if _REPO_ROOT_ENV
    else Path(__file__).resolve().parents[2]
)


_PHASE_12_SENTINELS = (
    "mindsos_knowledge/__init__.py",
    "mindsos_knowledge/identifiers.py",
    "mindsos_knowledge/exceptions.py",
)


@pytest.mark.parametrize("relpath", _PHASE_12_SENTINELS)
def test_phase_12_sentinel_exists(relpath: str) -> None:
    """Phase 12 mindsos_knowledge modules survive Dockerfile COPY."""
    full = _REPO_ROOT / relpath
    assert full.is_file(), f"Sentinel missing: {full}"
