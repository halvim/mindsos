"""Resident-brain conftest — live-FalkorDB skip/clean fixture.

Reachability probe + wipe, copied from the Phase-49 Integration C
precedent (pytest conftest discovery is package-scoped). The probe runs
first so a sidecar-less run (or ``-m 'not integration'``) never imports
``mindsos_server`` for the durable path.
"""

from __future__ import annotations

from typing import Iterator

import pytest


def _falkordb_reachable() -> bool:
    try:
        from mindsos_core.config import FalkorConfig
        from mindsos_core.persistence.client import FalkorClient

        client = FalkorClient(FalkorConfig.from_env())
        try:
            client.run_query("RETURN 1 AS ok", {})
        finally:
            client.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="function")
def falkordb_clean() -> Iterator[None]:
    """Function-scope clean FalkorDB; skips when no sidecar is reachable."""
    if not _falkordb_reachable():
        pytest.skip("resident-brain durable test requires a live FalkorDB sidecar")

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
