"""Phase 01 test fixtures."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

# Production code targets Python 3.12 (test image), where tomllib is stdlib.
# When tests run host-side on Python 3.10/3.11, fall back to the `tomli`
# backport. Harmless on 3.11+.
if sys.version_info < (3, 11):
    try:
        import tomli as _tomli_shim
        sys.modules.setdefault("tomllib", _tomli_shim)
    except ImportError:
        pass


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


def _run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["mindsos", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


@pytest.fixture
def cli() -> Callable[..., Any]:
    return _run_cli
