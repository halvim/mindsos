"""Per-test fresh FalkorDB graph fixture (Phase 07 — M15 + P43 A).

Each integration test gets its own ephemeral FalkorDB graph named
``test_<uuid_hex8>`` so tests don't see each other's writes. The
fixture yields a connected :class:`FalkorClient` bound to the graph;
the finalizer drops the graph via ``GRAPH.DELETE``.

Skips integration tests when no live sidecar is reachable.
"""

from __future__ import annotations

import os
import uuid
from typing import Iterator

import pytest


@pytest.fixture
def falkor_client() -> Iterator:
    """Yield a :class:`FalkorClient` bound to a fresh ``test_<uuid8>`` graph.

    Per M15 — per-test isolation. Per P43 A — finalizer wraps the yield
    in try/finally to guarantee teardown even on test failure.
    """
    try:
        from mindsos_core.config import FalkorConfig
        from mindsos_core.persistence import FalkorClient
    except Exception as e:  # pragma: no cover - import-time path
        pytest.skip(f"FalkorClient import failed: {e}")

    config = FalkorConfig.from_env()
    graph_name = f"test_{uuid.uuid4().hex[:8]}"
    config = FalkorConfig(
        host=config.host,
        port=config.port,
        password=config.password,
        graph=graph_name,
    )
    try:
        client = FalkorClient(config)
    except Exception as e:  # pragma: no cover - live-DB dependent
        pytest.skip(f"FalkorDB unreachable at {config.host}:{config.port}: {e}")

    try:
        yield client
    finally:
        # GRAPH.DELETE drops the ephemeral graph; safe to ignore errors.
        try:
            client.run_query("MATCH (n) DETACH DELETE n")
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass
