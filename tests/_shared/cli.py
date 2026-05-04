"""Shared subprocess CLI helper — extracted from Phase 02 conftest in Phase 03.

The leading-underscore on ``_run_cli`` is a private-convention signal;
no external importers are expected. Phase 02 and Phase 03 conftests
import it directly:

    from tests._shared.cli import _run_cli

History: Phase 02 §3.12 / Bug A — first draft replaced subprocess env
wholesale, breaking PATH / HOME inheritance. The merge-then-override
pattern below is the fix.
"""

from __future__ import annotations

import os
import subprocess
import sys


def _run_cli(
    *args: str, env: dict[str, str] | None = None, timeout: int = 30
) -> subprocess.CompletedProcess[str]:
    """Invoke ``mindsos <args...>`` via the installed console script.

    Falls back to ``python -m mindsos_cli`` when the entry point is not
    on PATH (e.g., host pytest on a checkout where the package isn't
    editable-installed).

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
