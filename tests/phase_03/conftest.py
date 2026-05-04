"""Phase 03 test fixtures.

Imports the subprocess CLI helper from ``tests/_shared/cli.py`` (extracted
from Phase 02 conftest in Phase 03).

Adds an **autouse fixture** that sets ``MINDSOS_STATE_DIR=tmp_path`` for
every test in the package — prevents leakage between the developer's
actual ``~/.mindsos/graph-*.json`` files and test runs.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests._shared import tomli_shim  # noqa: F401 — installs tomllib alias on 3.10/3.11
from tests._shared.cli import _run_cli


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


@pytest.fixture(autouse=True)
def _isolated_state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Autouse: every Phase 03 test gets a fresh ``MINDSOS_STATE_DIR``.

    Both in-process tests (`typer.testing.CliRunner` calling state.py
    helpers directly) and subprocess tests (`_run_cli`) read this env var.
    Function-scoped so each test starts with an empty state dir.
    """
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(state_dir))
    return state_dir
