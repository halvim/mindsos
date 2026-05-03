"""Phase 00 test fixtures."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import Any

import pytest


def _run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run `mindsos ...` via subprocess and return CompletedProcess."""
    return subprocess.run(
        ["mindsos", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


@pytest.fixture
def cli() -> Callable[..., Any]:
    """Return a callable that runs `mindsos <args...>` and returns CompletedProcess."""
    return _run_cli
