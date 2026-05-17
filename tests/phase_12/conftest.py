"""Phase 12 pytest fixtures.

Re-exports the shared `_run_cli` helper for subprocess CLI tests.
"""

from __future__ import annotations

from tests._shared.cli import _run_cli  # noqa: F401  — imported for fixtures
