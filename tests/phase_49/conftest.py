"""Phase 49 conftest — live-FalkorDB skip/clean fixture for the
Integration C scenario.

The skip + wipe fixture is copied from ``tests/phase_32/conftest.py``
(Integration B precedent; pytest conftest discovery is package-scoped —
no cross-phase fixture collision). The reachability probe runs FIRST so
sidecar-less collection/run (and ``-m 'not integration'``) never reaches
a ``mindsos_server`` import.

The ``mindsos_admin`` warm-up resolves the pre-existing
``admin`` ↔ ``persistence`` ↔ ``mindsos_admin`` import cycle under
isolated collection (``pytest tests/phase_49/``), mirroring
``tests/phase_44/conftest.py``. It is guarded so trees lacking the
server stack (e.g. an older interpreter without ``datetime.UTC``) still
collect the deterministic in-memory companion.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Iterator

import pytest

try:  # warm the server-side import cycle when the stack is importable
    importlib.import_module("mindsos_admin")
except Exception:  # pragma: no cover — companion-only trees skip the integration test
    pass


def _falkordb_reachable() -> bool:
    """Best-effort probe — skip the scenario when the FalkorDB sidecar is
    absent. Uses only ``mindsos_core`` (no server import)."""
    try:
        from mindsos_core.config import FalkorConfig
        from mindsos_core.persistence.client import FalkorClient

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
    """Function-scope clean FalkorDB for the Integration C scenario.

    Skips when no sidecar is reachable; otherwise wipes the graph once
    before and once after.
    """
    if not _falkordb_reachable():
        pytest.skip("Phase 49 Integration C scenario requires a live FalkorDB sidecar")

    def _wipe() -> None:
        try:
            from mindsos_core.config import FalkorConfig
            from mindsos_core.persistence.client import FalkorClient

            client = FalkorClient(FalkorConfig.from_env())
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
def scenario_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Fresh ``server.db`` + ``HOME`` for the L0 CLI substeps (token at
    ``HOME/.mindsos/token``)."""
    monkeypatch.setenv("MINDSOS_SERVER_DB", str(tmp_path / "server.db"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("MINDSOS_TOKEN", raising=False)
    yield tmp_path
