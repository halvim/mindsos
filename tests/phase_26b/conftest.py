"""Phase 26b conftest — scenario-scope FalkorDB cleanup.

Per Phase 26b design log R2-PB-1 (a): the integration scenario runs
CLI subprocesses across multiple invocations and DELIBERATELY
propagates state between them (subprocess #1's propose must be visible
to subprocess #2's ship; subprocess #2's ship must be visible to
step 10's stable-id assertion).

Phase 26a's `tests/phase_26a/conftest.py` defines only an
``in_memory_client`` fixture (not autouse); no inheritance conflict.
Repo-root `tests/conftest.py` only registers markers; no autouse
fixtures. The function-scope cleanup below runs ONCE per integration
test, before + after, NOT between substeps.
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
        pytest.skip("Phase 26b integration scenario requires live FalkorDB sidecar")

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
