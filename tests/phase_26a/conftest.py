"""Phase 26a shared fixtures.

Per Phase 26a design log R3-PB-3 (d) — per-session FalkorDB container
expected; per-test cleanup via ``GRAPH.LIST`` + ``GRAPH.DELETE`` for
the configured graph + tmpdir ``~/.mindsos``. The InMemoryClient
fixture is for unit tests that don't need a live FalkorDB.

For full E2E tests that exercise real Cypher: use the
``falkordb_client`` fixture; skip if FalkorDB is unreachable.
"""

from __future__ import annotations

import pytest

from mindsos_core.persistence.client import InMemoryClient


@pytest.fixture
def in_memory_client() -> InMemoryClient:
    """Fresh :class:`InMemoryClient` per test for unit-level wiring tests."""
    return InMemoryClient()
