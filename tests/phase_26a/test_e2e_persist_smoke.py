"""Phase 26a end-to-end FalkorDB persistence smoke (R2-PB-3 (b)).

Real FalkorDB container required; skips otherwise. Exercises the
wiring path Phase 26a is actually shipping:

1. ``bootstrap_kl_from_falkordb(client)`` mints+persists on first
   call; loads on second call (same Global preserved).
2. ``MetagraphRepository.persist`` re-persist idempotency
   (MERGE-safe — re-persist same Metagraph; no duplicate-create).
3. ``MetagraphLoader.find_by_name`` resolves the canonical Global
   id after mint+persist.

Per Phase 26a design log R3-PB-3 (d) — per-test cleanup via
``GRAPH.LIST`` + ``GRAPH.DELETE``; per-session container is the
test fixture lifecycle.
"""

from __future__ import annotations

import os

import pytest

from mindsos_core.config import FalkorConfig
from mindsos_core.exceptions import PersistenceError


def _falkordb_available() -> bool:
    """Probe FalkorDB reachability; skip E2E tests if unreachable."""
    try:
        from mindsos_core.persistence.client import FalkorClient

        client = FalkorClient(FalkorConfig.from_env())
        try:
            client.run_query("RETURN 1 AS ok", {})
            return True
        finally:
            client.close()
    except Exception:
        return False


skip_no_falkor = pytest.mark.skipif(
    not _falkordb_available(),
    reason="Phase 26a E2E smoke requires a reachable FalkorDB container.",
)


def _clean_falkor_graph() -> None:
    """Drop all nodes/edges in the configured FalkorDB graph."""
    from mindsos_core.persistence.client import FalkorClient

    client = FalkorClient(FalkorConfig.from_env())
    try:
        client.run_query("MATCH (n) DETACH DELETE n", {})
    finally:
        client.close()


@pytest.fixture
def clean_falkor():
    """Per-test cleanup of FalkorDB graph state."""
    _clean_falkor_graph()
    yield
    _clean_falkor_graph()


@skip_no_falkor
def test_bootstrap_mint_then_load_round_trip(clean_falkor) -> None:
    """First call mints+persists; second call loads same metagraph_id."""
    from mindsos_core.persistence.client import FalkorClient
    from mindsos_core.reconstruction.metagraph_loader import MetagraphLoader
    from mindsos_knowledge.knowledge_layer import _GLOBAL_METAGRAPH_NAME
    from mindsos_server.persistence import bootstrap_kl_from_falkordb

    # First call — mint path.
    client1 = FalkorClient(FalkorConfig.from_env())
    try:
        kl1 = bootstrap_kl_from_falkordb(client1)
        mg_id_1 = kl1.global_metagraph().metagraph_id
        assert mg_id_1  # non-empty
    finally:
        client1.close()

    # Second call — load path.
    client2 = FalkorClient(FalkorConfig.from_env())
    try:
        loader = MetagraphLoader(client2)
        found_id = loader.find_by_name(_GLOBAL_METAGRAPH_NAME)
        assert found_id == mg_id_1, (
            f"Subsequent find_by_name returned {found_id!r}; "
            f"expected {mg_id_1!r} from prior mint"
        )
        kl2 = bootstrap_kl_from_falkordb(client2)
        assert kl2.global_metagraph().metagraph_id == mg_id_1
    finally:
        client2.close()


@skip_no_falkor
def test_repository_persist_is_idempotent_across_calls(clean_falkor) -> None:
    """MERGE-idempotent persist (R7-F1) — re-persist doesn't duplicate."""
    from mindsos_core.persistence.client import FalkorClient
    from mindsos_core.persistence.metagraph_repository import (
        MetagraphRepository,
    )
    from mindsos_server.persistence import bootstrap_kl_from_falkordb

    client = FalkorClient(FalkorConfig.from_env())
    try:
        kl = bootstrap_kl_from_falkordb(client)
        repo = MetagraphRepository(client)
        # Re-persist the SAME Metagraph; should be no-op.
        repo.persist(kl.global_metagraph())
        # Verify only ONE Metagraph anchor exists with this name.
        result = client.run_query(
            "MATCH (m:Metagraph {name: $name}) RETURN count(m) AS n",
            {"name": kl.global_metagraph().name},
        )
        first = result.first()
        assert first is not None
        assert first["n"] == 1, (
            f"Re-persist created duplicate Metagraph anchors "
            f"(count={first['n']}); MERGE-idempotency broken"
        )
    finally:
        client.close()


@skip_no_falkor
def test_find_by_name_returns_none_on_empty_db(clean_falkor) -> None:
    """find_by_name returns None when no Metagraph anchor exists."""
    from mindsos_core.persistence.client import FalkorClient
    from mindsos_core.reconstruction.metagraph_loader import MetagraphLoader
    from mindsos_knowledge.knowledge_layer import _GLOBAL_METAGRAPH_NAME

    client = FalkorClient(FalkorConfig.from_env())
    try:
        loader = MetagraphLoader(client)
        assert loader.find_by_name(_GLOBAL_METAGRAPH_NAME) is None
    finally:
        client.close()
