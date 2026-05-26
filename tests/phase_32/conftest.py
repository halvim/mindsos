"""Phase 32 conftest — scenario-scope FalkorDB cleanup + state-dir.

Copied verbatim from ``tests/phase_26b/conftest.py`` per R1-PB-3 +
R4 §am-impl-3 (pytest conftest discovery is package-scoped — no
collision with 26b's fixtures of the same name).

Per Phase 32 R0-PB-1: the integration scenario runs CLI subprocesses
+ in-process Python helpers across substeps and deliberately
propagates state between them (admin login at substep 1b must be
visible to subsequent CLI calls via HOME-inherited token).

Function-scope cleanup runs ONCE per integration test, before + after,
NOT between substeps.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest

from mindsos_core.config import FalkorConfig
from mindsos_core.persistence.client import FalkorClient


def _falkordb_reachable() -> bool:
    """Best-effort probe — skip scenario when FalkorDB sidecar absent."""
    try:
        config = FalkorConfig.from_env()
        client = FalkorClient(config)
        try:
            client.run_query("RETURN 1 AS ok", {})
        finally:
            client.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="function")
def scenario_falkordb_clean(tmp_path: Path) -> Iterator[None]:
    """Function-scope clean state for the integration scenario.

    Wipes the configured FalkorDB graph ONCE before the scenario starts
    and ONCE after (best-effort). State propagates across subprocesses
    within the scenario.
    """
    if not _falkordb_reachable():
        pytest.skip("Phase 32 integration scenario requires live FalkorDB sidecar")

    def _wipe() -> None:
        try:
            config = FalkorConfig.from_env()
            client = FalkorClient(config)
            try:
                client.run_query("MATCH (n) DETACH DELETE n", {})
            finally:
                client.close()
        except Exception:
            pass

    _wipe()
    yield
    _wipe()


@pytest.fixture(scope="function")
def scenario_state_dir(tmp_path: Path) -> Iterator[Path]:
    """Function-scope ``~/.mindsos``-like state dir (per-scenario isolated).

    Sets ``MINDSOS_STATE_DIR`` env so CLI subprocesses share the SAME
    server.db across the scenario but each test gets a fresh DB.
    """
    state_dir = tmp_path / ".mindsos"
    state_dir.mkdir(parents=True, exist_ok=True)
    original = os.environ.get("MINDSOS_STATE_DIR")
    os.environ["MINDSOS_STATE_DIR"] = str(state_dir)
    try:
        yield state_dir
    finally:
        if original is None:
            os.environ.pop("MINDSOS_STATE_DIR", None)
        else:
            os.environ["MINDSOS_STATE_DIR"] = original
