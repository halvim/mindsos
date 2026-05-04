"""Phase 02 test fixtures."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests._shared.cli import _run_cli  # extracted from this conftest in Phase 03

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


@pytest.fixture
def cli() -> Callable[..., Any]:
    return _run_cli


@pytest.fixture
def isolated_state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Force ``mindsos identity registry`` to use a tmp state directory.

    Without this, tests would write into ``~/.mindsos`` and contaminate
    the developer's actual state (or fail in CI where ``$HOME`` isn't
    writable).
    """
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(state_dir))
    return state_dir
