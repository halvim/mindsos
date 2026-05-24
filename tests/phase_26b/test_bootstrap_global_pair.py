"""Phase 26b — bootstrap_global_pair_from_falkordb unit tests.

Per Phase 26b design log R4-PB-1 (a) + R6-PB-1 (a) + ADR-0118 §am4.

Covers:
1. Empty FalkorDB → mint+persist both canonical + pending; second call
   loads both with stable metagraph_ids (R6-PB-1 (a)).
2. Canonical pre-existing + pending missing → load canonical, mint+persist
   pending (cross-state heal).
3. Both pre-existing → load both; no new persist work.
4. Returned tuple types — KnowledgeLayer + bare Metagraph.
5. Pending Metagraph mirrors canonical role-set (Phase 24 PB-Z12(b) +
   inherited helper bootstrap_pending_global).
"""

from __future__ import annotations

import pytest

from mindsos_admin import (
    PENDING_GLOBAL_METAGRAPH_NAME,
    bootstrap_global,
    bootstrap_pending_global,
)
from mindsos_core import Metagraph
from mindsos_core.config import FalkorConfig
from mindsos_core.persistence.client import FalkorClient
from mindsos_core.persistence.metagraph_repository import MetagraphRepository
from mindsos_knowledge.knowledge_layer import (
    _GLOBAL_METAGRAPH_NAME,
    KnowledgeLayer,
)
from mindsos_server.persistence import bootstrap_global_pair_from_falkordb


def _falkordb_reachable() -> bool:
    try:
        client = FalkorClient(FalkorConfig.from_env())
        try:
            client.run_query("RETURN 1 AS ok", {})
        finally:
            client.close()
        return True
    except Exception:
        return False


@pytest.fixture()
def fresh_falkordb_client():
    if not _falkordb_reachable():
        pytest.skip("requires live FalkorDB sidecar")
    client = FalkorClient(FalkorConfig.from_env())
    client.run_query("MATCH (n) DETACH DELETE n", {})
    try:
        yield client
    finally:
        try:
            client.run_query("MATCH (n) DETACH DELETE n", {})
        finally:
            client.close()


@pytest.mark.integration
def test_mint_then_load_canonical_id_stable(fresh_falkordb_client) -> None:
    """First call mints+persists; second call loads same canonical id."""
    kl1, _ = bootstrap_global_pair_from_falkordb(fresh_falkordb_client)
    canonical_id_1 = kl1.global_metagraph().metagraph_id

    kl2, _ = bootstrap_global_pair_from_falkordb(fresh_falkordb_client)
    canonical_id_2 = kl2.global_metagraph().metagraph_id

    assert canonical_id_1 == canonical_id_2


@pytest.mark.integration
def test_mint_then_load_pending_id_stable(fresh_falkordb_client) -> None:
    """First call mints+persists pending; second call loads same pending id."""
    _, pending_1 = bootstrap_global_pair_from_falkordb(fresh_falkordb_client)
    pending_id_1 = pending_1.metagraph_id

    _, pending_2 = bootstrap_global_pair_from_falkordb(fresh_falkordb_client)
    pending_id_2 = pending_2.metagraph_id

    assert pending_id_1 == pending_id_2


@pytest.mark.integration
def test_returns_knowledge_layer_and_metagraph(fresh_falkordb_client) -> None:
    """Tuple shape: (KnowledgeLayer, Metagraph)."""
    kl, pending = bootstrap_global_pair_from_falkordb(fresh_falkordb_client)
    assert isinstance(kl, KnowledgeLayer)
    assert isinstance(pending, Metagraph)
    assert kl.global_metagraph().name == _GLOBAL_METAGRAPH_NAME
    assert pending.name == PENDING_GLOBAL_METAGRAPH_NAME


@pytest.mark.integration
def test_pending_mirrors_canonical_role_set(fresh_falkordb_client) -> None:
    """Pending role-set parity with canonical (Phase 24 PB-Z12(b))."""
    kl, pending = bootstrap_global_pair_from_falkordb(fresh_falkordb_client)
    canonical_roles = {g.role for g in kl.global_metagraph().graphs.values()}
    pending_roles = {g.role for g in pending.graphs.values()}
    assert canonical_roles == pending_roles


@pytest.mark.integration
def test_canonical_preexisting_pending_missing_heals(fresh_falkordb_client) -> None:
    """Canonical persisted by prior helper; no pending. Pair helper mints pending.

    Phase 26a's bootstrap_kl_from_falkordb persists canonical only; if a
    fresh-Phase-26b run hits a Phase-26a-only FalkorDB state, the pair
    helper must mint+persist pending without re-minting canonical.
    """
    # Seed canonical via the Phase 15a `bootstrap_global` admin helper +
    # MetagraphRepository persist; no pending anywhere.
    canonical_mg = bootstrap_global(importers=())
    repo = MetagraphRepository(fresh_falkordb_client)
    repo.persist(canonical_mg)
    canonical_id_seeded = canonical_mg.metagraph_id

    kl, pending = bootstrap_global_pair_from_falkordb(fresh_falkordb_client)
    # Canonical loaded — same id as seeded.
    assert kl.global_metagraph().metagraph_id == canonical_id_seeded
    # Pending minted + persisted.
    assert pending.metagraph_id is not None
    # Second call reads pending back stably.
    _, pending_2 = bootstrap_global_pair_from_falkordb(fresh_falkordb_client)
    assert pending_2.metagraph_id == pending.metagraph_id
