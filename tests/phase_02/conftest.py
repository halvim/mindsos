"""Phase 02 test fixtures."""

from __future__ import annotations

import os
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


def _run_cli(
    *args: str, env: dict[str, str] | None = None, timeout: int = 30
) -> subprocess.CompletedProcess[str]:
    """Invoke `mindsos <args...>` via the installed console script.

    Falls back to `python -m mindsos_cli` when the entry point is not on
    PATH (e.g., host pytest on a checkout where the package isn't editable-
    installed). The fall-back is best-effort and exists so a Mac developer
    can iterate without `pip install -e .`.

    ``env`` is **merged** with the parent process environment. Tests pass
    ``env={"MINDSOS_STATE_DIR": "/tmp/x"}`` and expect PATH / HOME / etc.
    to be inherited; replacing the entire env breaks the fallback to
    ``python -m mindsos_cli`` (no PYTHONPATH, no PATH to find the
    interpreter etc.).
    """
    merged_env: dict[str, str] | None
    if env is None:
        merged_env = None
    else:
        merged_env = {**os.environ, **env}

    try:
        return subprocess.run(
            ["mindsos", *args],
            capture_output=True,
            text=True,
            env=merged_env,
            timeout=timeout,
        )
    except FileNotFoundError:
        return subprocess.run(
            [sys.executable, "-m", "mindsos_cli", *args],
            capture_output=True,
            text=True,
            env=merged_env,
            timeout=timeout,
        )


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
