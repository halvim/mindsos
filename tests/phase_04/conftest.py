"""Phase 04 test fixtures.

Same shape as Phase 03 conftest:

* Imports the shared subprocess CLI helper.
* Imports the tomli_shim (Python 3.10/3.11 sandbox compatibility).
* Autouse ``MINDSOS_STATE_DIR`` isolation fixture so schema-*.json /
  graph-*.json never leak between tests or to the developer's
  ``~/.mindsos/``.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests._shared import tomli_shim  # noqa: F401 — installs tomllib alias on 3.10/3.11
from tests._shared.cli import _run_cli


def _repo_root() -> Path:
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
    """Autouse: every Phase 04 test gets a fresh ``MINDSOS_STATE_DIR``."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(state_dir))
    return state_dir
